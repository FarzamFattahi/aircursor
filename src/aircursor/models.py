from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class DetectedHand:
    landmarks: tuple[Point, ...]
    handedness: str
    confidence: float
    tracking_id: str | None = None

    def __post_init__(self) -> None:
        if len(self.landmarks) != 21:
            raise ValueError("MediaPipe hands must contain exactly 21 landmarks")

    @property
    def wrist(self) -> Point:
        return self.landmarks[0]

    @property
    def thumb_tip(self) -> Point:
        return self.landmarks[4]

    @property
    def index_tip(self) -> Point:
        return self.landmarks[8]

