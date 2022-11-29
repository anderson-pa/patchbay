import asyncio
import sys
import os
from os.path import dirname
from pathlib import Path

from pint import UnitRegistry, set_application_registry

__version__ = '0.0.6'

loop = asyncio.get_event_loop()

os.environ['QT_API'] = 'PySide2'

ureg = UnitRegistry()
ureg.define('division = 1 * count = div')

qty = ureg.Quantity
set_application_registry(ureg)

root_path = Path(dirname(__file__))
if hasattr(sys, "_MEIPASS"):  # if pyinstaller used
    root_path = Path(sys._MEIPASS)

try:
    # use the patchbay style for matplotlib
    import matplotlib.pyplot as plt

    plt.style.use(str(root_path / 'matplotlibrc'))
except ImportError:
    pass


def device_manager(pkg_names=None):
    from patchbay.hardware.device_manager import DeviceManager
    if pkg_names is None:
        pkg_names = []
    return DeviceManager(pkg_names)


_module_err_msg = ("The package '{package}' is required. "
                   "Try 'pip install {package}' from the command line.")


def launch_gui(filename=None):
    # check the requirements and import
    failed_requirements = []
    try:
        from PySide2.QtWidgets import QApplication
        from PySide2.QtGui import QIcon
    except ModuleNotFoundError:
        failed_requirements.append('PySide2')

    try:
        from qasync import QEventLoop
    except ModuleNotFoundError:
        failed_requirements.append('qasync')

    if failed_requirements:
        for package in failed_requirements:
            print(_module_err_msg.format(package=package))
        sys.exit()

    # if on Windows, change the taskbar icon
    try:
        from PySide2.QtWinExtras import QtWin
        myappid = f'andersonics.llc.patchbay.{__version__}'
        QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    from patchbay.qt.patchbay_ui import Patchbay

    #  launch the GUI
    app = QApplication(sys.argv)
    app.setOrganizationName('Andersonics')
    app.setOrganizationDomain('andersonics.llc')
    app.setApplicationName('patchbay')
    app.setWindowIcon(QIcon(str(root_path / 'resources' / 'pb.svg')))

    try:
        # use proper scaling for matplotlib figures in the UI
        plt.matplotlib.rcParams['figure.dpi'] = app.desktop().physicalDpiX()
    except NameError:
        pass

    asyncio.set_event_loop(QEventLoop(app))

    patchbay_ui = Patchbay(filename=filename)
    return app.exec_()
