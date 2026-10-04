from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AirCursorConfig:
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    preferred_hand: str = "Auto"
    drag_hold_ms: int = 650
    scroll_enabled: bool = True
    mirror_preview: bool = True
    margin_x: float = 0.14
    margin_y: float = 0.12
    min_cutoff: float = 1.25
    beta: float = 0.018
    derivative_cutoff: float = 1.0
    pointer_gain: float = 1.0

    def validate(self) -> None:
        if self.camera_width <= 0 or self.camera_height <= 0:
            raise ValueError("Camera dimensions must be positive")
        if self.preferred_hand not in {"Auto", "Left", "Right"}:
            raise ValueError("preferred_hand must be Auto, Left, or Right")
        if not 0 <= self.margin_x < 0.5 or not 0 <= self.margin_y < 0.5:
            raise ValueError("Control margins must be in [0, 0.5)")
        if self.drag_hold_ms < 0:
            raise ValueError("drag_hold_ms cannot be negative")

