from PySide2.QtCore import QSettings
from PySide2.QtWidgets import QMainWindow, QFileDialog, QFrame

from patchbay.patch import load_patch, BaseUiPatch
from patchbay.qt import actions


class Patchbay(QMainWindow):
    """MainWindow for Patchbay."""

    def __init__(self, filename=None):
        super().__init__()
        self.patch = None

        self.actions = {name: getattr(actions, f'{name}_action')(self, connect)
                        for name, connect in [('close', self.close_patch),
                                              ('open', self.open_patch),
                                              ('quit', self.close)]}
        self.toolbar = None

        # initialize the UI
        self.setWindowTitle('patchbay')
        self.create_menubar()
        self.create_statusbar()
        self.create_toolbar()

        self.restore_settings()
        self.set_patch(filename)
        self.show()

    def create_menubar(self):
        """Create the patchbay menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu('&File')
        for item in ['open', 'close', 'quit']:
            file_menu.addAction(self.actions[item])

        help_menu = menubar.addMenu('&Help')

    def create_statusbar(self):
        """Create the patchbay status bar."""
        self.statusBar()

    def create_toolbar(self):
        """Create the primary patchbay toolbar."""
        self.toolbar = self.addToolBar('Patchbay Toolbar')
        self.toolbar.setObjectName('PatchbayToolbar')

    def save_settings(self):
        """Save settings to persistent storage for future use."""
        settings = QSettings()
        settings.setValue('MainWindow/Geometry', self.saveGeometry())
        settings.setValue('MainWindow/State', self.saveState())

    # noinspection PyTypeChecker
    def restore_settings(self):
        """Restore settings from persistent storage."""
        settings = QSettings()
        self.restoreGeometry(settings.value('MainWindow/Geometry', b''))
        self.restoreState(settings.value('MainWindow/State', b''))

        self.actions['close'].setDisabled(self.patch is None)

    def closeEvent(self, event):
        """Override parent closeEvent to save settings first."""
        self.save_settings()
        QMainWindow.closeEvent(self, event)

    def open_patch(self):
        """Select and open a new patch to use."""
        f_name, _ = QFileDialog.getOpenFileName(self, caption='Select a patch to load',
                                                filter='Patches (*.pbp, *.py)')
        self.set_patch(f_name)

    def set_patch(self, filename):
        if filename is None:
            return
        patch_module = load_patch(filename)
        if issubclass(patch_module.Patch, BaseUiPatch):
            self.close_patch()
            self.patch = patch_module.Patch(self)

            self.setCentralWidget(self.patch.ui)
            self.actions['close'].setDisabled(False)

    def close_patch(self):
        """Close the current patch."""
        if self.patch:
            self.patch.close()
        self.setCentralWidget(QFrame())
        self.actions['close'].setDisabled(True)
