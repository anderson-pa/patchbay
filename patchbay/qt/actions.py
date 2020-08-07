from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QAction


def open_action(parent, connect_to=None):
    action = QAction('&Open...', parent)
    action.setStatusTip('Open a patch.')
    if connect_to is None:
        connect_to = parent.open
    action.triggered.connect(connect_to)
    return action


def close_action(parent, connect_to=None):
    action = QAction('&Close', parent)
    action.setShortcut(QKeySequence('Ctrl+W'))
    action.setStatusTip('Close the current patch.')
    if connect_to is None:
        connect_to = parent.close
    action.triggered.connect(connect_to)
    return action


def quit_action(parent, connect_to=None):
    action = QAction('&Quit', parent)
    action.setShortcut(QKeySequence('Ctrl+Q'))
    action.setStatusTip('Quit.')
    if connect_to is None:
        connect_to = parent.quit
    action.triggered.connect(connect_to)
    return action
