from patchbay.hardware import scpi


class AgilentN3300Load(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

        self.source = None

    def _get_versions(self, v_string):
        versions = {'Firmware': v_string,
                    'SCPI': self.device.query('system:version?')}

        return versions
