from __future__ import annotations

import ctypes
from abc import ABC, abstractmethod
from ctypes import wintypes


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class InputEvent(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("data", InputUnion)]


class BaseInputController(ABC):
    @abstractmethod
    def screen_size(self) -> tuple[int, int]: ...

    @abstractmethod
    def move(self, x: int, y: int) -> None: ...

    @abstractmethod
    def click(self) -> None: ...

    @abstractmethod
    def left_down(self) -> None: ...

    @abstractmethod
    def left_up(self) -> None: ...

    @abstractmethod
    def scroll(self, amount: int) -> None: ...

    @abstractmethod
    def release_all(self) -> None: ...


class WindowsInputController(BaseInputController):
    LEFT_DOWN = 0x0002
    LEFT_UP = 0x0004
    WHEEL = 0x0800

    def __init__(self) -> None:
        if not hasattr(ctypes, "windll"):
            raise OSError("WindowsInputController is available only on Windows")
        self.user32 = ctypes.windll.user32
        self.user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(InputEvent), ctypes.c_int)
        self.user32.SendInput.restype = wintypes.UINT
        self._left_held = False

    def _send(self, *flags: int, wheel: int = 0) -> None:
        events = (InputEvent * len(flags))(*(
            InputEvent(0, InputUnion(mi=MouseInput(0, 0, wheel & 0xFFFFFFFF, flag, 0, 0)))
            for flag in flags
        ))
        if self.user32.SendInput(len(events), events, ctypes.sizeof(InputEvent)) != len(events):
            raise OSError("Windows rejected mouse input. Stop control; use apps at the same privilege level.")

    def screen_size(self) -> tuple[int, int]:
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def move(self, x: int, y: int) -> None:
        width, height = self.screen_size()
        if not self.user32.SetCursorPos(max(0, min(width - 1, int(x))),
                                      max(0, min(height - 1, int(y)))):
            raise OSError("Windows rejected cursor movement")

    def double_click_time(self) -> float:
        return self.user32.GetDoubleClickTime() / 1000.0

    def click(self) -> None:
        self._send(self.LEFT_DOWN, self.LEFT_UP)

    def left_down(self) -> None:
        if not self._left_held:
            self._send(self.LEFT_DOWN)
            self._left_held = True

    def left_up(self) -> None:
        if self._left_held:
            self._send(self.LEFT_UP)
            self._left_held = False

    def scroll(self, amount: int) -> None:
        self._send(self.WHEEL, wheel=int(amount * 120))

    def release_all(self) -> None:
        # Release even if a prior event failed before internal state updated.
        self._send(self.LEFT_UP)
        self._left_held = False
