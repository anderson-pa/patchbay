import asyncio

from pint import UnitRegistry, set_application_registry

loop = asyncio.get_event_loop()

ureg = UnitRegistry()
qty = ureg.Quantity
set_application_registry(ureg)

