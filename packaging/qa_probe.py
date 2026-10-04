"""Self-test executed inside the updated frozen runtime, without camera access."""
import ctypes
import json
import time
from pathlib import Path


def run(destination):
    from app.config.settings import SettingsStore
    from app.gestures.gesture_manager import GestureManager
    from app.gestures.states import InteractionMode
    from app.platform.windows_input import WindowsInputController
    from app.pointer.tap_stabilizer import TapStabilizer
    from app.ui.main_window import MainWindow
    from app.ui.theme import STYLESHEET
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from aircursor.models import DetectedHand, Point

    path = Path(destination)
    app = QApplication([])
    app.setStyleSheet(STYLESHEET)
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(path.parent))
    controller = WindowsInputController()
    assert controller.screen_size()[0] > 0
    stabilizer = TapStabilizer()
    assert stabilizer.double_tap_window > 0
    stabilizer.stabilize((100, 200), InteractionMode.POINTER, 0)
    assert stabilizer.stabilize((150, 250), InteractionMode.PINCH, 0.1) == (100, 200)
    points = [Point(0.5, 0.5) for _ in range(21)]
    points[4], points[8] = Point(0.4, 0.3), Point(0.45, 0.3)
    points[5], points[17] = Point(0.3, 0.6), Point(0.7, 0.6)
    hand = DetectedHand(tuple(points), "Right", 0.99)
    manager = GestureManager(controller, scrolling=False)
    assert manager.update(hand, 0).mode is InteractionMode.PINCH
    assert manager.update(hand, 0.03).mode is InteractionMode.PINCH
    points[8] = Point(0.7, 0.3)
    opened = DetectedHand(tuple(points), "Right", 0.99)
    manager.update(opened, 0.1)
    result = manager.update(opened, 0.13)
    assert result.tap_completed and controller.pending == ["click"]
    controller.pending.clear()  # No physical click during the runtime probe.
    store = SettingsStore(path.parent / "qa-settings.json")
    window = MainWindow(store, controller)
    window.show()
    app.processEvents()
    window.showNormal()
    window.resize(1280, 850)
    app.processEvents()
    assert window.primary.text() == "Start Hand Control"
    window.grab().save(str(path.with_suffix(".png")))
    from app.ui.settings_dialog import SettingsDialog
    from PySide6.QtWidgets import QTabWidget
    dialog = SettingsDialog(store, window)
    tabs = dialog.findChild(QTabWidget)
    for index in range(tabs.count()):
        if tabs.tabText(index) == "Gestures":
            tabs.setCurrentIndex(index)
    dialog.show()
    app.processEvents()
    assert dialog.drag.minimum() == 650
    dialog.grab().save(str(path.with_name(path.stem + "-gestures.png")))
    dialog.close()
    window.force_exit = True
    window.close()
    app.processEvents()
    path.write_text(json.dumps({"passed": True, "cameraPreviewStarted": False,
                               "checks": ["frozen imports", "Windows input adapter",
                                          "gesture transitions", "queued click", "target lock",
                                          "Qt main window startup"]}, indent=2), encoding="utf-8")


def native_probe(destination):
    """Send real Windows input only to a dedicated foreground test window."""
    from app.platform.windows_input import WindowsInputController
    from PySide6.QtWidgets import QApplication, QWidget

    events = []

    class Target(QWidget):
        def mousePressEvent(self, event):
            events.append(("down", event.position().x(), event.position().y()))

        def mouseDoubleClickEvent(self, event):
            events.append(("double", event.position().x(), event.position().y()))

        def mouseReleaseEvent(self, event):
            events.append(("up", event.position().x(), event.position().y()))

        def mouseMoveEvent(self, event):
            if event.buttons():
                events.append(("drag", event.position().x(), event.position().y()))

    app = QApplication([])
    window = Target()
    window.setWindowTitle("AirCursor input verification — closes automatically")
    window.resize(320, 200)
    window.move(120, 120)
    window.show()
    window.raise_()
    window.activateWindow()
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.SetForegroundWindow.argtypes = (ctypes.c_void_p,)
    user32.ShowWindow.argtypes = (ctypes.c_void_p, ctypes.c_int)
    # Start-Process Hidden controls the first native ShowWindow call. Make
    # this dedicated input-test target explicitly visible before injecting.
    user32.ShowWindow(int(window.winId()), 5)
    user32.SetForegroundWindow(int(window.winId()))

    def pump(seconds=0.1):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.005)

    from ctypes import wintypes
    old = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(old))
    controller = WindowsInputController()
    try:
        pump()
        if user32.GetForegroundWindow() != int(window.winId()):
            raise RuntimeError("Test window could not receive focus; no clicks sent")
        scale = window.devicePixelRatioF()
        origin = wintypes.POINT(round(80 * scale), round(80 * scale))
        user32.ClientToScreen.argtypes = (ctypes.c_void_p, ctypes.POINTER(wintypes.POINT))
        user32.ClientToScreen(int(window.winId()), ctypes.byref(origin))
        px, py = origin.x, origin.y
        controller.move(px, py)
        controller.left_down()
        controller.move(px, py)
        pump(0.03)
        controller.left_up()
        controller.move(px, py)
        pump(0.05)
        controller.left_down()
        controller.move(px, py)
        pump(0.03)
        controller.left_up()
        controller.move(px, py)
        pump()
        cursor = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(cursor))
        user32.WindowFromPoint.argtypes = (wintypes.POINT,)
        user32.WindowFromPoint.restype = ctypes.c_void_p
        assert [event[0] for event in events if event[0] != "drag"] == ["down", "up", "double", "up"], (events, scale, px, py, cursor.x, cursor.y, user32.WindowFromPoint(cursor), int(window.winId()))
        assert all(event[1:] == (80.0, 80.0) for event in events), events
        pump(controller.controller.double_click_time() + 0.1)
        controller.left_down()
        controller.move(px + round(50 * scale), py + round(30 * scale))
        pump()
        controller.left_up()
        controller.move(px + round(50 * scale), py + round(30 * scale))
        pump()
        assert any(event[0] == "drag" for event in events), events
        assert events[-1][0] == "up" and abs(events[-1][1] - 130) <= 0.5 and abs(events[-1][2] - 110) <= 0.5, events
        Path(destination).write_text(json.dumps({"passed": True, "events": events,
                                                "doubleClickTime": controller.controller.double_click_time()}, indent=2), encoding="utf-8")
    finally:
        controller.release_all()
        user32.SetCursorPos(old.x, old.y)
        window.close()
        app.processEvents()
