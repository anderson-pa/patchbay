from PySide2.QtWidgets import QMainWindow


class Patchbay(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('patchbay')
        self.show()
