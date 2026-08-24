from __future__ import annotations

import math
from dataclasses import dataclass, field

from .gestures import InteractionMode


@dataclass(slots=True)
class CoordinateMapper:
    screen_width: int
    screen_height: int
    margin_x: float = 0.14
    margin_y: float = 0.12
    mirrored_input: bool = False

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def normalize(self, x: float, y: float) -> tuple[float, float]:
        if self.mirrored_input:
            x = 1.0 - x
        nx = (x - self.margin_x) / (1.0 - 2.0 * self.margin_x)
        ny = (y - self.margin_y) / (1.0 - 2.0 * self.margin_y)
        return self._clamp(nx, 0.0, 1.0), self._clamp(ny, 0.0, 1.0)

    def map(self, x: float, y: float) -> tuple[int, int]:
        nx, ny = self.normalize(x, y)
        return (
            round(nx * max(0, self.screen_width - 1)),
            round(ny * max(0, self.screen_height - 1)),
        )


class LowPassFilter:
    def __init__(self) -> None:
        self.value: float | None = None

    def filter(self, value: float, alpha: float) -> float:
        if self.value is None:
            self.value = value
        else:
            self.value = alpha * value + (1.0 - alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = None


class OneEuroFilter:
    """Velocity-adaptive low-pass filter from Casiez et al."""

    def __init__(
        self,
        min_cutoff: float = 1.25,
        beta: float = 0.018,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._position = [LowPassFilter(), LowPassFilter()]
        self._derivative = [LowPassFilter(), LowPassFilter()]
        self._last_t: float | None = None
        self._last_raw: tuple[float, float] | None = None

    @staticmethod
    def alpha(dt: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 1e-6))
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def reset(self) -> None:
        for item in (*self._position, *self._derivative):
            item.reset()
        self._last_t = None
        self._last_raw = None

    def filter(self, point: tuple[float, float], timestamp: float) -> tuple[float, float]:
        if self._last_t is None or self._last_raw is None:
            self._last_t = timestamp
            self._last_raw = point
            return tuple(
                self._position[index].filter(value, 1.0)
                for index, value in enumerate(point)
            )

        dt = max(1e-6, min(0.25, timestamp - self._last_t))
        output: list[float] = []
        for index, value in enumerate(point):
            derivative = (value - self._last_raw[index]) / dt
            filtered_derivative = self._derivative[index].filter(
                derivative, self.alpha(dt, self.d_cutoff)
            )
            cutoff = self.min_cutoff + self.beta * abs(filtered_derivative)
            output.append(self._position[index].filter(value, self.alpha(dt, cutoff)))

        self._last_t = timestamp
        self._last_raw = point
        return output[0], output[1]


class PointerGain:
    def __init__(self, multiplier: float = 1.0) -> None:
        self.multiplier = max(0.1, multiplier)
        self.previous: tuple[float, float] | None = None

    def reset(self) -> None:
        self.previous = None

    def apply(self, point: tuple[float, float]) -> tuple[float, float]:
        if self.previous is None:
            self.previous = point
            return point
        dx = point[0] - self.previous[0]
        dy = point[1] - self.previous[1]
        distance = math.hypot(dx, dy)
        adaptive = min(self.multiplier + distance / 450.0, self.multiplier + 0.35)
        result = self.previous[0] + dx * adaptive, self.previous[1] + dy * adaptive
        self.previous = result
        return result


@dataclass(slots=True)
class TapStabilizer:
    double_tap_window: float = 0.38
    anchor: tuple[float, float] | None = field(init=False, default=None)
    lock_until: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self.anchor: tuple[float, float] | None = None
        self.lock_until = 0.0

    def reset(self) -> None:
        self.anchor = None
        self.lock_until = 0.0

    def stabilize(
        self,
        point: tuple[float, float],
        mode: InteractionMode,
        now: float,
        tap_completed: bool = False,
    ) -> tuple[float, float]:
        if mode is InteractionMode.DRAG:
            self.reset()
            return point
        if mode is InteractionMode.PINCH and self.anchor is None:
            self.anchor = point
        if tap_completed:
            self.lock_until = now + self.double_tap_window
        if self.anchor is not None and (mode is InteractionMode.PINCH or now < self.lock_until):
            return self.anchor
        if now >= self.lock_until:
            self.anchor = None
        return point
