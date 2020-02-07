from PySide2.QtWidgets import QDoubleSpinBox, QSpinBox
import pint


class PQSpinBox(QSpinBox):
    def __init__(self, unit:pint.unit):
        super().__init__()
        self.unit = unit
        self.setSuffix(f' {unit:~P}')

    def setValue(self, val:pint.quantity):
        super().setValue(val.to(self.unit).magnitude)

    def value(self) -> int:
        return super().value() * self.unit


class PQDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, unit:pint.unit):
        super().__init__()
        self.unit = unit
        self.setSuffix(f' {unit:~P}')

    def setValue(self, val:pint.quantity):
        super().setValue(val.to(self.unit).magnitude)

    def value(self) -> float:
        return super().value() * self.unit
