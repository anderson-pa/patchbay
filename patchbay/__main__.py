import asyncio
import sys

module_err_msg = ("The package '{package}' is required. "
                  "Try 'pip install {package}' from the command line.")


def launch_gui():

    # check the requirements and import
    failed_requirements = []
    try:
        from PySide2.QtWidgets import QApplication
    except ModuleNotFoundError:
        failed_requirements.append('PySide2')

    try:
        from asyncqt import QEventLoop
    except ModuleNotFoundError:
        failed_requirements.append('asyncqt')

    if failed_requirements:
        for package in failed_requirements:
            print(module_err_msg.format(package=package))
        sys.exit()

    from patchbay.qt.patchbay_ui import Patchbay

    #  launch the GUI
    app = QApplication(sys.argv)
    app.setOrganizationName('Andersonics')
    app.setOrganizationDomain('andersonics.llc')
    app.setApplicationName('patchbay')

    asyncio.set_event_loop(QEventLoop(app))

    patchbay_ui = Patchbay()
    return app.exec_()


def main_gui(args=None):
    return_code = launch_gui()
    sys.exit(return_code)


def main(args=None):
    print('Launching the console!')
    #  TODO: Look into CLI frameworks (click, cement, cliff...)


if __name__ == '__main__':
    main_gui()
