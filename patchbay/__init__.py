import asyncio
import sys
from os.path import dirname
from pathlib import Path

from pint import UnitRegistry, set_application_registry

__version__ = '0.0.3'

loop = asyncio.get_event_loop()

ureg = UnitRegistry()
ureg.define('division = 1 * count = div')

qty = ureg.Quantity
set_application_registry(ureg)

root_path = Path(dirname(__file__))
if hasattr(sys, "_MEIPASS"):  # if pyinstaller used
    root_path = Path(sys._MEIPASS)
