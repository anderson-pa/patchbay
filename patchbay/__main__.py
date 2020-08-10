import asyncio
import sys

import click

from patchbay import root_path

module_err_msg = ("The package '{package}' is required. "
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
    app.setWindowIcon(QIcon(str(root_path / 'resources' / 'pb.svg')))

    asyncio.set_event_loop(QEventLoop(app))

    patchbay_ui = Patchbay(filename=filename)
    return app.exec_()


def main_gui():
    sys.exit(launch_gui())


@click.command()
@click.argument('filename', required=False,
                type=click.Path(exists=True, dir_okay=False))
def main(filename):
    """Launch a patch file

    \f
    :param filename:
    :return:
    """
    print('Welcome to Patchbay!')

    return launch_gui(filename)


if __name__ == '__main__':
    main_gui()
