from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol

from .models import DetectedHand


class InteractionMode(Enum):
    PAUSED = auto()
    TRACKING_LOST = auto()
    POINTER = auto()
    PINCH = auto()
    DRAG = auto()
    SCROLL = auto()


class PinchState(Enum):
    OPEN = auto()
    PINCH_CANDIDATE = auto()
    PINCHED = auto()
    RELEASE_CANDIDATE = auto()


class DragAction(Enum):
    NONE = auto()
    CLICK = auto()
    BUTTON_DOWN = auto()
    BUTTON_UP = auto()


def normalized_pinch_distance(hand: DetectedHand) -> float:
    palm_width = max(
        math.dist(
            (hand.landmarks[5].x, hand.landmarks[5].y),
            (hand.landmarks[17].x, hand.landmarks[17].y),
        ),
        1e-6,
    )
    return math.dist(
        (hand.thumb_tip.x, hand.thumb_tip.y),
        (hand.index_tip.x, hand.index_tip.y),
    ) / palm_width


def pinch_midpoint(hand: DetectedHand) -> tuple[float, float]:
    return (
        (hand.thumb_tip.x + hand.index_tip.x) / 2.0,
        (hand.thumb_tip.y + hand.index_tip.y) / 2.0,
    )


@dataclass(slots=True)
class PinchDetector:
    start_threshold: float = 0.30
    release_threshold: float = 0.40
    confirm_frames: int = 2
    release_frames: int = 2
    state: PinchState = field(init=False, default=PinchState.OPEN)
    _count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.state = PinchState.OPEN
        self._count = 0

    def reset(self) -> None:
        self.state = PinchState.OPEN
        self._count = 0

    def update(self, distance: float) -> PinchState:
        if self.state is PinchState.OPEN:
            if distance <= self.start_threshold:
                self.state = PinchState.PINCH_CANDIDATE
                self._count = 1
        elif self.state is PinchState.PINCH_CANDIDATE:
            if distance <= self.start_threshold:
                self._count += 1
                if self._count >= self.confirm_frames:
                    self.state = PinchState.PINCHED
                    self._count = 0
            else:
                self.reset()
        elif self.state is PinchState.PINCHED:
            if distance >= self.release_threshold:
                self.state = PinchState.RELEASE_CANDIDATE
                self._count = 1
        elif self.state is PinchState.RELEASE_CANDIDATE:
            if distance >= self.release_threshold:
                self._count += 1
                if self._count >= self.release_frames:
                    self.reset()
            else:
                self.state = PinchState.PINCHED
                self._count = 0
        return self.state


@dataclass(slots=True)
class DragController:
    hold_seconds: float = 0.52
    started_at: float | None = field(init=False, default=None)
    dragging: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.started_at: float | None = None
        self.dragging = False

    def pinch_started(self, now: float) -> DragAction:
        self.started_at = now
        self.dragging = False
        return DragAction.NONE

    def tick(self, now: float) -> DragAction:
        if (
            self.started_at is not None
            and not self.dragging
            and now - self.started_at >= self.hold_seconds
        ):
            self.dragging = True
            return DragAction.BUTTON_DOWN
        return DragAction.NONE

    def pinch_released(self, now: float) -> DragAction:
        del now
        if self.started_at is None:
            return DragAction.NONE
        action = DragAction.BUTTON_UP if self.dragging else DragAction.CLICK
        self.started_at = None
        self.dragging = False
        return action

    def cancel(self) -> DragAction:
        action = DragAction.BUTTON_UP if self.dragging else DragAction.NONE
        self.started_at = None
        self.dragging = False
        return action


def finger_extended(hand: DetectedHand, tip: int, pip: int) -> bool:
    return hand.landmarks[tip].y < hand.landmarks[pip].y


@dataclass(slots=True)
class ScrollDetector:
    activation_frames: int = 5
    dead_zone: float = 0.008
    active: bool = field(init=False, default=False)
    _stable: int = field(init=False, default=0)
    _last_y: float | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.active = False
        self._stable = 0
        self._last_y: float | None = None

    def update(self, hand: DetectedHand) -> int:
        pose = (
            finger_extended(hand, 8, 6)
            and finger_extended(hand, 12, 10)
            and not finger_extended(hand, 16, 14)
            and not finger_extended(hand, 20, 18)
        )
        if not pose:
            self.reset()
            return 0
        self._stable += 1
        y = (hand.landmarks[8].y + hand.landmarks[12].y) / 2.0
        if not self.active:
            if self._stable >= self.activation_frames:
                self.active = True
                self._last_y = y
            return 0
        delta = (self._last_y if self._last_y is not None else y) - y
        self._last_y = y
        if abs(delta) < self.dead_zone:
            return 0
        return max(-5, min(5, int(delta * 90)))


class InputController(Protocol):
    def click(self) -> None: ...
    def left_down(self) -> None: ...
    def left_up(self) -> None: ...
    def scroll(self, amount: int) -> None: ...
    def release_all(self) -> None: ...


@dataclass(frozen=True, slots=True)
class GestureResult:
    mode: InteractionMode
    pinch_distance: float
    tap_completed: bool = False


class GestureManager:
    def __init__(
        self,
        input_controller: InputController,
        drag_hold_ms: int = 650,
        scrolling: bool = True,
    ) -> None:
        self.input = input_controller
        self.pinch = PinchDetector()
        self.drag = DragController(drag_hold_ms / 1000.0)
        self.scroll = ScrollDetector()
        self.scrolling = scrolling
        self._previous_pinch = PinchState.OPEN
        self._armed = True

    def reset(self) -> None:
        if self.drag.cancel() is DragAction.BUTTON_UP:
            self.input.left_up()
        self.input.release_all()
        self.pinch.reset()
        self.scroll.reset()
        self._previous_pinch = PinchState.OPEN
        # Reacquiring a closed hand must not create a fresh click or drag.
        self._armed = False

    def update(self, hand: DetectedHand, now: float) -> GestureResult:
        if hasattr(self.input, "set_hand_intent"):
            self.input.set_hand_intent(hand.wrist.x, hand.wrist.y)
        distance = normalized_pinch_distance(hand)
        if not math.isfinite(distance):
            self.reset()
            return GestureResult(InteractionMode.TRACKING_LOST, distance)
        if not self._armed:
            if distance < self.pinch.release_threshold:
                return GestureResult(InteractionMode.POINTER, distance)
            self._armed = True
        state = self.pinch.update(distance)
        tap_completed = False

        if state is PinchState.PINCHED and self._previous_pinch is PinchState.PINCH_CANDIDATE:
            self.drag.pinch_started(now)
        if state is PinchState.OPEN and self._previous_pinch is PinchState.RELEASE_CANDIDATE:
            action = self.drag.pinch_released(now)
            if action is DragAction.CLICK:
                self.input.click()
                tap_completed = True
            elif action is DragAction.BUTTON_UP:
                self.input.left_up()

        # Opening at the hold boundary is a release, not a new drag.
        if state is PinchState.PINCHED and self.drag.tick(now) is DragAction.BUTTON_DOWN:
            self.input.left_down()

        self._previous_pinch = state
        if self.drag.dragging:
            return GestureResult(InteractionMode.DRAG, distance, tap_completed)
        if state in {PinchState.PINCH_CANDIDATE, PinchState.PINCHED, PinchState.RELEASE_CANDIDATE}:
            self.scroll.reset()
            return GestureResult(InteractionMode.PINCH, distance, tap_completed)

        amount = self.scroll.update(hand) if self.scrolling else 0
        if self.scroll.active:
            if amount:
                self.input.scroll(amount)
            return GestureResult(InteractionMode.SCROLL, distance, tap_completed)
        return GestureResult(InteractionMode.POINTER, distance, tap_completed)
