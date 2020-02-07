import asyncio

from pint import UnitRegistry, set_application_registry

__all__ = ['hardware', 'qt']

loop = asyncio.get_event_loop()

unit = UnitRegistry()
qty = unit.Quantity
set_application_registry(unit)
