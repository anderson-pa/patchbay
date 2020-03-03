import dwf

from patchbay.hardware.device_utils import (DeviceDescriptor, ResourceManager,
                                            get_device_handler)


class DwfManager(ResourceManager):
    def __init__(self):
        super().__init__('dwf')
