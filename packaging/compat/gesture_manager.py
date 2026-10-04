"""Adapter for the original packaged Qt worker's result enum."""
from dataclasses import dataclass

from app.gestures.states import InteractionMode

from aircursor.gestures import GestureManager as CoreManager


@dataclass
class GestureResult:
    mode: InteractionMode
    pinch_distance: float
    tap_completed: bool = False


class GestureManager(CoreManager):
    def __init__(self, input_controller, drag_hold_ms=650, scrolling=True):
        # Prevent old short hold settings turning an ordinary tap into drag.
        super().__init__(input_controller, max(drag_hold_ms, 650), scrolling)

    def update(self, hand, now):
        result = super().update(hand, now)
        return GestureResult(InteractionMode[result.mode.name], result.pinch_distance,
                             result.tap_completed)
