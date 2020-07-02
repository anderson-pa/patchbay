from PySide2.QtCore import QSettings
from PySide2.QtWidgets import QMainWindow


class Patchbay(QMainWindow):
    """MainWindow for Patchbay."""
    def __init__(self):
        super().__init__()

        # initialize the UI
        self.setWindowTitle('patchbay')
        self.create_menubar()
        self.create_statusbar()
        self.create_toolbar()

        self.restore_settings()
        self.show()

    def create_menubar(self):
        """Create the patchbay menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu('&File')
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

    def closeEvent(self, event):
        """Override parent closeEvent to save settings first."""
        self.save_settings()
        QMainWindow.closeEvent(self, event)
