from patchbay.hardware import scpi


class AgilentN3300Load(scpi.ScpiNode):

    def __init__(self, device):
        super().__init__(device)

        self.current = None
        self.voltage = None
        scpi.ScpiFactory.add_subsystem(self, 'measure', measure_cmds)
        scpi.ScpiFactory.add_subsystem(self, 'channel', channel_cmds)
        scpi.ScpiFactory.add_subsystem(self, 'current', [])
        scpi.ScpiFactory.add_subsystem(self, 'voltage', [])
        scpi.ScpiFactory.add_subsystem(self, 'resistance', r_cmds)

        scpi.ScpiFactory.add_subsystem(self.current, 'protection', c_protect_cmds)

    def _get_versions(self, v_string):
        versions = {'Firmware': v_string,
                    'SCPI': self.device.query('system:version?')}

        return versions


min_max_keywords = {f'{key}_keywords': ['min', 'max']
                    for key in ['query',]}

measure_cmds = [('voltage', 'voltage', 'qty', 'V', {'can_write': False}),
                ('current', 'current', 'qty', 'A', {'can_write': False}),
                ('power', 'power', 'qty', 'W', {'can_write': False}),
                ]

r_cmds = [('resistance', ':res', 'qty', 'ohm', min_max_keywords),
          ]

c_protect_cmds = [('level', 'lev', 'qty', 'A'),
                  ('delay', 'del', 'qty', 's'),
                  ('enabled', 'state', 'bool', None)
                  ]

channel_cmds = [('channel', ':channel', 'number', 'int'),
                ('enabled', ':input', 'bool', None),
                ('function', ':func', 'choice', {'CR': 'RES', 'CV': 'VOLT', 'CC': 'CURR'})
                ]
