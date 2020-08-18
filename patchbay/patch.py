import os
import sys
import weakref
from importlib.util import spec_from_file_location, module_from_spec

from PySide2.QtWidgets import QFrame

from patchbay import ureg

original_path = sys.path


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
    sys.path.insert(0, os.path.dirname(os.path.realpath(f_name)))
    patch_module = module_from_spec(spec)
    spec.loader.exec_module(patch_module)
    return patch_module


def close_patch(patch_module):
    sys.path = original_path
    patch_module.close()
