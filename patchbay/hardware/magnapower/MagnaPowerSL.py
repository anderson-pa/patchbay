from patchbay.hardware import scpi
from patchbay.hardware.subsystem import CmdDef

prototype_definitions = {}


# Magna-Power Electronics Inc., SL60-25, S/N:1164-2572, F/W:8.7\r\n
# IP: 192.168.50.204

class MagnaPowerSLSupply(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

        self.source = None
        scpi.ScpiFactory.add_subsystem(self, 'measure', measure_cmds)
        scpi.ScpiFactory.add_subsystem(self, 'output', output_cmds)
        scpi.ScpiFactory.add_subsystem(self, 'source', source_cmds)

    def _get_versions(self, v_string):
        # names = ['Firmware', 'Hardware']
        # versions = {n: v for n, v in zip(names, v_string.split('-'))}
        versions = {}
        # scpi version
        versions['SCPI'] = self.device.query('system:version?')
        return versions


measure_cmds = [CmdDef('voltage', 'voltage', 'qty', 'V', {'can_write': False}),
                CmdDef('current', 'current', 'qty', 'A', {'can_write': False}),
                ]

output_cmds = [('enabled', 'state', 'bool', None, {'can_write':False}),
               ('enabled', ('start', 'stop'), 'bool', None,
                {'can_query': False, 'split_cmd': True})
               ]

min_max_keywords = {f'{key}_keywords': ['min', 'max']
                    for key in ['query',]}

source_cmds = [('voltage', 'volt', 'qty', 'V', min_max_keywords),
               ('triggered_voltage', 'volt:trig', 'qty', 'V', min_max_keywords),
               ('current', 'curr', 'qty', 'A', min_max_keywords),
               ('triggered_current', 'curr:trig', 'qty', 'A', min_max_keywords),
               ]

