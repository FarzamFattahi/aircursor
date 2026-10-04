"""Applied after the original Qt main-window module; preserve its controls."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QLabel

MainWindow = globals()["MainWindow"]
_original_init = MainWindow.__init__
_original_show = MainWindow.show
_original_close = MainWindow.closeEvent


def _improved_init(self, store, input_controller):
    store.set("drag_hold_ms", max(650, store.get("drag_hold_ms", 650)))
    _original_init(self, store, input_controller)
    self.setMinimumSize(760, 560)
    self.resize(1280, 850)
    self.preview.setMinimumHeight(300)
    self.preview.setText("Place your hand in view. The thumb–index midpoint controls the full screen.")
    self.instructions = QLabel("Pinch and release to click  ·  Repeat quickly to double-click  ·  Hold 0.65 seconds, then move to drag")
    self.instructions.setWordWrap(True)
    self.instructions.setAccessibleName("Hand control instructions")
    self.centralWidget().layout().addWidget(self.instructions)
    self._layout_preferences = QSettings("AirCursor", "WindowLayout")
    geometry = self._layout_preferences.value("geometry")
    self._first_large_show = geometry is None
    if geometry is not None:
        self.restoreGeometry(geometry)


def _improved_show(self):
    _original_show(self)
    if self._first_large_show:
        self._first_large_show = False
        self.showMaximized()


def _improved_close(self, event):
    self._layout_preferences.setValue("geometry", self.saveGeometry())
    _original_close(self, event)


MainWindow.__init__ = _improved_init
MainWindow.show = _improved_show
MainWindow.closeEvent = _improved_close
