import pyvisa

from patchbay.hardware.device_utils import (DeviceDescriptor, ResourceManager,
                                            get_device_handler)
from patchbay.hardware.scpi import ScpiNode


class PyvisaManager(ResourceManager):
    def __init__(self, backend='@py'):
        super().__init__('pyvisa')
        self.rm = pyvisa.ResourceManager(backend)

    def refresh(self):
        devices = []
        for address in self.rm.list_resources():
            device, descriptor = self.open_scpi_resource(address)
            if descriptor is not None:
                devices.append(descriptor)
        self.devices = devices

    def open_scpi_resource(self, address):
        try:
            device = self.rm.open_resource(address)
        except pyvisa.errors.VisaIOError:
            return None, None

        original_timeout = device.timeout
        device.timeout = 200

        try:
            idn_response = device.query('*idn?')
        except pyvisa.errors.VisaIOError:
            return None, None

        device.timeout = original_timeout

        scpi_node = ScpiNode(device)
        device_handler = get_device_handler(scpi_node.make, scpi_node.model)

        if device_handler is not None:
            device = device_handler(device)
            idn_response = [getattr(device, s) for s in
                            ['make', 'model', 'serial', 'versions']]

        descriptor = DeviceDescriptor(*idn_response, address)

        return device, descriptor

    def open_device(self, address):
        device, descriptor = self.open_scpi_resource(address)
        return device
