"""Keep the visible drag delay consistent with the interaction classifier."""
SettingsDialog = globals()["SettingsDialog"]
_original_init = SettingsDialog.__init__


def _improved_init(self, store, parent=None):
    _original_init(self, store, parent)
    self.drag.setMinimum(650)
    self.drag.setValue(max(650, self.drag.value()))


SettingsDialog.__init__ = _improved_init
