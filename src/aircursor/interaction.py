"""Order each frame's pointer movement and button actions atomically."""
from __future__ import annotations

import math
import time


class FrameInputController:
    """Buffer gesture button events until the stabilized target is available.

    Drag-down uses the last pinned position, then movement continues with the
    button held. Click/up are dispatched after positioning the cursor.
    Tracking-loss cleanup bypasses the queue and releases immediately.
    """

    def __init__(self, controller) -> None:
        self.controller = controller
        self.pending: list[str] = []
        self.previous: tuple[int, int] | None = None
        self.hand_intent: tuple[float, float] | None = None
        self.last_click_intent: tuple[float, float] | None = None
        self.last_click_position: tuple[int, int] | None = None
        self.last_click_at = -float("inf")
        self.clock = time.monotonic
        self.double_click_window = (controller.double_click_time()
                                    if hasattr(controller, "double_click_time") else 0.5)

    def set_hand_intent(self, x: float, y: float) -> None:
        self.hand_intent = (x, y)

    def screen_size(self) -> tuple[int, int]:
        return self.controller.screen_size()

    def click(self) -> None:
        self.pending.append("click")

    def left_down(self) -> None:
        self.pending.append("left_down")

    def left_up(self) -> None:
        self.pending.append("left_up")

    def scroll(self, amount: int) -> None:
        self.controller.scroll(amount)

    def move(self, x: int, y: int) -> None:
        actions, self.pending = self.pending, []
        try:
            if "left_down" in actions:
                self.controller.move(*(self.previous or (x, y)))
                self.controller.left_down()
            self.controller.move(x, y)
            for action in actions:
                if action != "left_down":
                    if action == "click":
                        now = self.clock()
                        same_target = (self.hand_intent is not None
                                       and self.last_click_intent is not None
                                       and math.dist(self.hand_intent, self.last_click_intent) < 0.035)
                        if (same_target and now - self.last_click_at <= self.double_click_window
                                and self.last_click_position is not None):
                            x, y = self.last_click_position
                            self.controller.move(x, y)
                        self.last_click_at = now
                        self.last_click_position = (x, y)
                        self.last_click_intent = self.hand_intent
                    getattr(self.controller, action)()
            self.previous = (x, y)
        except Exception:
            self.release_all()
            raise

    def release_all(self) -> None:
        self.pending.clear()
        self.previous = None
        self.last_click_at = -float("inf")
        self.last_click_position = None
        self.last_click_intent = None
        self.controller.release_all()
