import asyncio
import sys

from PySide2.QtWidgets import QApplication
from asyncqt import QEventLoop

from qt.patchbay_ui import Patchbay


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setOrganizationName('Andersonics')
    app.setOrganizationDomain('andersonics.llc')
    app.setApplicationName('patchbay')

    asyncio.set_event_loop(QEventLoop(app))

    patchbay_ui = Patchbay()
    sys.exit(app.exec_())
