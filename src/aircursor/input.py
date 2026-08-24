from __future__ import annotations

import ctypes
from abc import ABC, abstractmethod


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
        self._left_held = False

    def screen_size(self) -> tuple[int, int]:
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def move(self, x: int, y: int) -> None:
        self.user32.SetCursorPos(int(x), int(y))

    def click(self) -> None:
        self.user32.mouse_event(self.LEFT_DOWN, 0, 0, 0, 0)
        self.user32.mouse_event(self.LEFT_UP, 0, 0, 0, 0)

    def left_down(self) -> None:
        if not self._left_held:
            self.user32.mouse_event(self.LEFT_DOWN, 0, 0, 0, 0)
            self._left_held = True

    def left_up(self) -> None:
        if self._left_held:
            self.user32.mouse_event(self.LEFT_UP, 0, 0, 0, 0)
            self._left_held = False

    def scroll(self, amount: int) -> None:
        self.user32.mouse_event(self.WHEEL, 0, 0, int(amount * 120), 0)

    def release_all(self) -> None:
        self.left_up()
