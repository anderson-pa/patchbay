from collections import namedtuple

from importlib import import_module

mfr_nice_name = {
    'HEWLETT-PACKARD': 'HP',
}

device_series_type = {
    ('HP', '33120A'): ('33120A', 'SignalGenerator'),
}


def get_device_handler(make, model):
    try:
        make_nice = mfr_nice_name[make]
        series, device_type = device_series_type[(make_nice, model)]
    except KeyError:
        return None
    else:
        handler_module = import_module(f'.{make_nice}{series}',
                                       f'patchbay.hardware.{make_nice.lower()}')
        return getattr(handler_module, f'{make_nice}{series}{device_type}')


DeviceDescriptor = namedtuple('DeviceDescriptor',
                              'make, model, serial, versions, address')


class ResourceManager:
    def __init__(self, pkg_name):
        self.pkg_name = pkg_name
        self.devices = []

    def refresh(self):
        pass
