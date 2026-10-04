"""Position-before-click bridge for the original packaged Qt worker."""
from aircursor.input import WindowsInputController as NativeController
from aircursor.interaction import FrameInputController


class WindowsInputController(FrameInputController):
    def __init__(self):
        super().__init__(NativeController())
