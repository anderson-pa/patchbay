from patchbay.hardware import scpi


class TektronixMSOOscilloscope(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

    def _get_versions(self, v_string):
        names = {'CF': 'Codes/Formats',
                 'FV': 'Firmware'}
        versions = {names[n]: v for s in v_string.split(' ')
                    for n, v in [s.split(':')]}
        return versions
