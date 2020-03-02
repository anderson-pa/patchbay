from patchbay.node import Node
from patchbay.hardware.device_utils import mfr_nice_name


class HP33120ASignalGenerator(Node):
    def __init__(self, device):
        self.device = device

        idn = self.device.query('*idn?').split(',')
        self.make = mfr_nice_name[idn[0]]
        self.model = idn[1]
        self.serial = self._get_serial(idn[2])
        self.versions = self._get_versions(idn[3])

        channel_specs = {(1, 'carrier'): ['enabled']
                         }

        super().__init__(channel_specs)

    def get_channel_attribute(self, channel_id, attr_name):
        super().get_channel_attribute(channel_id, attr_name)

    def set_channel_attribute(self, channel_id, attr_name, value):
        super().set_channel_attribute(channel_id, attr_name, value)

    def _get_versions(self, v_string):
        names = ['Main Generator Processor',
                 'Input/Output Processor',
                 'Front-panel Processor']
        versions = {n: v for n, v in zip(names, v_string.split('-'))}

        # scpi version
        versions['SCPI'] = self.device.query('system:version?')
        return versions

    def _get_serial(self, s_string):
        """Get the serial number for the device

        The 33120A does not store serial number internally by default but
        suggests storing it in the calibration string field. Better than using
        a blank or the '0' in the third field of the *idn? response.

        :param s_string:
        :return:

        """
        return self.device.query('calibration:string?')
