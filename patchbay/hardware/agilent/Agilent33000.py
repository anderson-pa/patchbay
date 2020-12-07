from patchbay.hardware import scpi


class Agilent33000SignalGenerator(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

        self.source = None
        scpi.ScpiFactory.add_subsystem(self, 'source', source_cmds,
                                       num_channels=2)
        # scpi.ScpiFactory.add_subsystem(self.source, 'am')

    def _get_versions(self, v_string):
        names = ['Firmware', 'Front-panel Firmware',
                 'Power Supply Controller Firmware',
                 'FPGA', 'PCBA']
        if self.model[2] == 6:
            names[2] = 'Main Board'

        versions = {n: v for n, v in zip(names, v_string.split('-'))}

        # scpi version
        versions['SCPI'] = self.device.query('system:version?')
        return versions


source_cmds = [('enabled', ':output{idx}', 'bool'),
               ('frequency', 'frequency', 'qty', 'Hz',
                {'query_keywords': ['min', 'max'],
                 'write_keywords': ['min', 'max', 'default']}),
               ('voltage', 'voltage', 'qty', 'V',
                {'query_keywords': ['min', 'max'],
                 'write_keywords': ['min', 'max', 'default']}),
               ('shape', 'function', 'choice',
                {'sinusoid': 'SIN', 'square': 'SQU', }),
               ]
