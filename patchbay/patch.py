import weakref
from importlib.util import spec_from_file_location, module_from_spec

from PySide2.QtWidgets import QFrame

from patchbay import ureg


class BasePatch:
    ureg = ureg

    def __init__(self, parent):
        self._parent = weakref.ref(parent)


class BaseUiPatch(BasePatch):
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = QFrame()
        self.widgets = {}


def load_patch(f_name):
    spec = spec_from_file_location("PatchModule", f_name)
    patch_module = module_from_spec(spec)
    spec.loader.exec_module(patch_module)
    return patch_module
