from PySide2.QtCore import Qt
from PySide2.QtWidgets import QDoubleSpinBox, QSpinBox
import pint


class PQSpinBox(QSpinBox):
    """Units-aware QSpinBox."""
    def __init__(self, unit:pint.unit):
        super().__init__()
        self.unit = unit
        self.setSuffix('')
        self.setAlignment(Qt.AlignRight)

    def setValue(self, val:pint.quantity):
        super().setValue(val.to(self.unit).magnitude)

    def value(self) -> int:
        return super().value() * self.unit

    def setSuffix(self, suffix:str) -> None:
        super().setSuffix(f' {self.unit:~P}{suffix}')


class PQDoubleSpinBox(QDoubleSpinBox):
    """Units-aware QDoubleSpinBox."""
    def __init__(self, unit:pint.unit):
        super().__init__()
        self.unit = unit
        self.setSuffix('')
        self.setAlignment(Qt.AlignRight)

    def setValue(self, val:pint.quantity):
        super().setValue(val.to(self.unit).magnitude)

    def value(self) -> float:
        return super().value() * self.unit

    def setSuffix(self, suffix:str) -> None:
        super().setSuffix(f' {self.unit:~P}{suffix}')
