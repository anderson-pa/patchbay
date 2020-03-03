from importlib import import_module
from importlib.util import find_spec


class DeviceManager:
    """Class for finding physical hardware and loading controllers.

    """

    def __init__(self, pkg_names=None):
        if not pkg_names:
            pkg_names = ['pyvisa', 'dwf']
        self.managers = self.find_package_managers(pkg_names)
        self.refresh_devices()

    @property
    def devices(self):
        return [dev for mgr in self.managers for dev in mgr.devices]

    def refresh_devices(self):
        for manager in self.managers:
            manager.refresh()

    def open_device(self, make, model):
        for manager in self.managers:
            for descriptor in manager.devices:
                if descriptor.make == make and descriptor.model == model:
                    return manager.open_device(descriptor.address)

    def open_ethernet_device(self, ip_address):
        for manager in self.managers:
            if manager.pkg_name == 'pyvisa':
                address = f'TCPIP::{ip_address}::INSTR'
                return manager.open_device(address)
        return None  # if none of the managers are for pyvisa

    @staticmethod
    def find_package_managers(pkg_names):
        managers = []
        for pkg in pkg_names:
            spec = find_spec(pkg)
            if spec is not None:
                module = import_module(f'.{pkg}_manager',
                                       'patchbay.hardware')
                manager = getattr(module, f'{pkg.capitalize()}Manager')
                managers.append(manager())

        return managers
