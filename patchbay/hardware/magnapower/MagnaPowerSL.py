from patchbay.hardware import scpi
from patchbay.hardware.subsystem import CmdDef

prototype_definitions = {}


class MagnaPowerSLSupply(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

        self.source = None
        scpi.ScpiFactory.add_subsystem(self, 'measure', measure_cmds)
        scpi.ScpiFactory.add_subsystem(self, 'output', output_cmds)
        scpi.ScpiFactory.add_subsystem(self, 'source', source_cmds)

    def _get_serial(self, idn_part):
        # device returns field as 'S/N:xxxx-yyyy', cut off prefix including colon
        return idn_part.split(':')[-1]

    def _get_versions(self, v_string):
        names = ['Firmware', 'Hardware']
        versions = self.device.query('system:version?').split(', ')
        versions = {n: v.split(' ')[-1] for n, v in zip(names, versions)}
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

