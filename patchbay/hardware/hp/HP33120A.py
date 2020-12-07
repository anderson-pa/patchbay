from patchbay.hardware import scpi


class HP33120ASignalGenerator(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

        self.source = None
        scpi.ScpiFactory.add_subsystem(self, 'source')
        scpi.ScpiFactory.add_subsystem(self.source, 'am')

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


# scpi.ScpiFactory.graft_subsystem('system', HP33120ASignalGenerator)
