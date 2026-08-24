from __future__ import annotations

import math
from dataclasses import dataclass, field

from .models import DetectedHand


@dataclass(slots=True)
class HandSelector:
    preferred: str = "Auto"
    grace_frames: int = 8
    match_radius: float = 0.18
    _last_wrist: tuple[float, float] | None = field(init=False, default=None)
    _last_label: str | None = field(init=False, default=None)
    _missing: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._last_wrist: tuple[float, float] | None = None
        self._last_label: str | None = None
        self._missing = 0

    def select(self, hands: list[DetectedHand]) -> DetectedHand | None:
        if not hands:
            self._missing += 1
            if self._missing > self.grace_frames:
                self.reset()
            return None

        candidates = hands
        if self.preferred != "Auto":
            preferred = [hand for hand in hands if hand.handedness == self.preferred]
            if preferred:
                candidates = preferred

        selected: DetectedHand
        if self._last_wrist is not None:
            nearest = min(
                candidates,
                key=lambda hand: math.dist(
                    self._last_wrist, (hand.wrist.x, hand.wrist.y)
                ),
            )
            if math.dist(self._last_wrist, (nearest.wrist.x, nearest.wrist.y)) <= self.match_radius:
                selected = nearest
            else:
                selected = max(candidates, key=lambda hand: hand.confidence)
        else:
            selected = max(candidates, key=lambda hand: hand.confidence)

        self._last_wrist = selected.wrist.x, selected.wrist.y
        self._last_label = selected.handedness
        self._missing = 0
        return selected
