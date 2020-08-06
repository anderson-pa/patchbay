from patchbay import ureg


class BasePatch:
    ureg = ureg

    def __init__(self, parent):
        self._parent = parent


class BaseUiPatch(BasePatch):
    def __init__(self, parent):
        super().__init__(parent)
        self.widgets = {}
