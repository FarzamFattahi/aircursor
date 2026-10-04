"""Keep the existing Qt worker API, using Windows' double-click interval."""
import ctypes

from aircursor.gestures import InteractionMode
from aircursor.pointer import TapStabilizer as CoreStabilizer


class TapStabilizer(CoreStabilizer):
    def __init__(self, double_tap_window=None):
        if double_tap_window is None:
            double_tap_window = ctypes.windll.user32.GetDoubleClickTime() / 1000.0
        super().__init__(double_tap_window)

    def stabilize(self, point, mode, now, tap_completed=False):
        return super().stabilize(point, InteractionMode[mode.name], now, tap_completed)
