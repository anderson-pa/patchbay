import pytest
from mock import Mock
from pint import DimensionalityError
from patchbay.hardware import subsystem as subs


@subs.add_can_querywrite_keywords
def convert_identity(_):
    """Get a converter for passing along whatever is given.

    :param _: dummy for signature matching
    :return: ValueConverter for anything
    """
    return subs.ValueConverter(lambda x: x, lambda y: y)


class DummySubsystemFactory(subs.SubsystemFactory):
    converters = {'ident': convert_identity}

    @staticmethod
    def query_func(command, converter, keyword=None):

        def q_func(self):
            return converter(self.device.query(command, keyword))

        return q_func

    @staticmethod
    def write_func(command, converter, keyword=None):

        def w_func_kw(self):
            return self.device.write(command, keyword)

        def w_func(self, val=None):
            return self.device.write(command, converter(val))

        return w_func_kw if keyword else w_func

    @staticmethod
    def hook_get_new_subsystem(new_subsystem):
        new_subsystem.dummy_var = 'dummy_var'


cmds = [subs.CmdDef(*args) for args in
        [["enabled", 'blah', "bool"],
         ["shape", 'shapecmd', "choice", {'sinusoid': 'SIN', 'square': 'SQU'}],
         ["frequency", 'freqcmd', "qty", "Hz",
          {"query_keywords": ('min', 'max'),
           "write_keywords": ('min', 'max', 'default')}],]]

choice_map = {'shape': {'sinusoid': 'SIN', 'square': 'SQU', 'triangle': 'TRI',
                        'ramp': 'RAMP', 'noise': 'NOIS', 'custom': 'USER'},
              'amplitude_unit': {'Vpp': 'VPP', 'Vrms': 'VRMS', 'dBm': 'DBM'}}


@pytest.fixture(scope='function')
def blank_system():
    subsystem = subs.SubsystemFactory._get_new_subsystem('Dummy')
    return subsystem(Mock(**{'device.query.return_value': 'abc'}))


def test_convert_bool():
    vc = subs.convert_bool()

    # test queries
    for val in ['1', 1, 4]:
        assert vc.query(val) is True
    for val in ['0', 0]:
        assert vc.query(val) is False

    # test writes
    for val in [True, 1, '1']:
        assert vc.write(val) == 1
    for val in [False, 0, '0']:
        assert vc.write(val) == 0


def test_convert_num():
    vc = subs.convert_num('int')

    # test queries
    for val, expected in [('1', 1), (5, 5), (8.65, 8)]:
        assert vc.query(val) == expected

    # test writes
    for val, expected in [('1', '1')]:
        assert vc.write(val) == expected


def test_convert_qty():
    vc = subs.convert_qty('m')

    # test queries
    assert vc.query('5.0') == 5 * subs.ureg.m
    assert vc.query(0.543) == 543 * subs.ureg.mm
    assert vc.query(3) != 3 * subs.ureg.s
    assert vc.query('2.5') != 2.5

    # test writes
    assert vc.write(8 * subs.ureg.m) == 8
    assert vc.write(8297 * subs.ureg.mm) == 8.297

    with pytest.raises(DimensionalityError):
        vc.write(5)
    with pytest.raises(DimensionalityError):
        vc.write(5 * subs.ureg.J)


def test_convert_qty_percent():
    vc = subs.convert_qty('%')

    # test queries
    assert vc.query('5.0') == 0.05
    assert vc.query(15.0) == 0.15

    # test writes
    assert vc.write(43) == 4300
    assert vc.write(.021) == 2.1


def test_convert_choices():
    choices = {a: a.capitalize() for a in ['a', 'b', 'c', 'd']}
    vc = subs.convert_choice(choices)

    for key, val in choices.items():
        assert vc.query(val) == key
        assert vc.write(key) == val

    with pytest.raises(KeyError):
        vc.query('foo')
    with pytest.raises(KeyError):
        vc.write('bar')


def test_add_cmd_qw(blank_system):
    s = blank_system
    DummySubsystemFactory.add_cmd(s, 'test', 'do_test', 'ident',
                                  query_keywords=['qkw1', 'qkw2'],
                                  write_keywords=['wkw1', 'wkw2'])

    assert s.test == 'abc'
    assert s.device.query.call_args.args == ('do_test', None)

    for kw in ['qkw1', 'qkw2']:
        x = getattr(s, f'test_{kw}')
        assert s.device.query.call_args.args == ('do_test', kw)

    s.test = 4
    assert s.device.write.call_args.args == ('do_test', 4)

    for kw in ['wkw1', 'wkw2']:
        getattr(s, f'test_to_{kw}')()
        assert s.device.write.call_args.args == ('do_test', kw)


def test_add_cmd_q(blank_system):
    s = blank_system
    DummySubsystemFactory.add_cmd(blank_system, 'test', 'do_test', 'ident',
                                  can_write=False,
                                  query_keywords=['qkw1', 'qkw2'],
                                  write_keywords=['wkw1'])

    assert not hasattr(s, 'test')
    assert not hasattr(s, 'set_test')
    assert not hasattr(s, 'test_to_wkw1')

    assert s.get_test() == 'abc'
    assert s.device.query.call_args.args == ('do_test', None)

    for kw in ['qkw1', 'qkw2']:
        x = getattr(s, f'test_{kw}')
        assert s.device.query.call_args.args == ('do_test', kw)


def test_add_cmd_w(blank_system):
    s = blank_system
    DummySubsystemFactory.add_cmd(blank_system, 'test', 'do_test', 'ident',
                                  can_query=False,
                                  query_keywords=['qkw1'],
                                  write_keywords=['wkw1', 'wkw2'])

    assert not hasattr(s, 'test')
    assert not hasattr(s, 'get_test')
    assert not hasattr(s, 'test_qkw1')

    s.set_test('123')
    assert s.device.write.call_args.args == ('do_test', '123')

    for kw in ['wkw1', 'wkw2']:
        getattr(s, f'test_to_{kw}')()
        assert s.device.write.call_args.args == ('do_test', kw)


def test_combine_cmd_qw(blank_system):
    s = blank_system
    DummySubsystemFactory.add_cmds(blank_system,
                                   [('test', 'querytest', 'ident', None,
                                     {'can_write': False,
                                      'query_keywords': ['qkw1'],
                                      'write_keywords':['wkw1', 'wkw2']}),
                                    ('test', 'writetest', 'ident', None,
                                     {'can_query': False,
                                      'query_keywords': ['qkw1'],
                                      'write_keywords': ['wkw1', 'wkw2']}),
                                    ])

    assert not hasattr(s, 'set_test')
    assert not hasattr(s, 'get_test')

    s.test = '123'
    assert s.device.write.call_args.args == ('writetest', '123')

    for kw in ['qkw1']:
        x = getattr(s, f'test_{kw}')
        assert s.device.query.call_args.args == ('querytest', kw)
    for kw in ['wkw1', 'wkw2']:
        getattr(s, f'test_to_{kw}')()
        assert s.device.write.call_args.args == ('writetest', kw)


def test_combine_cmd_wq(blank_system):
    s = blank_system
    DummySubsystemFactory.add_cmds(blank_system,
                                   [('test', 'writetest', 'ident', None,
                                     {'can_query': False,
                                      'query_keywords': ['qkw1'],
                                      'write_keywords': ['wkw1', 'wkw2']}),
                                    ('test', 'querytest', 'ident', None,
                                     {'can_write': False,
                                      'query_keywords': ['qkw1'],
                                      'write_keywords': ['wkw1', 'wkw2']})
                                    ])

    assert not hasattr(s, 'set_test')
    assert not hasattr(s, 'get_test')

    s.test = '123'
    assert s.device.write.call_args.args == ('writetest', '123')

    for kw in ['qkw1']:
        x = getattr(s, f'test_{kw}')
        assert s.device.query.call_args.args == ('querytest', kw)
    for kw in ['wkw1', 'wkw2']:
        getattr(s, f'test_to_{kw}')()
        assert s.device.write.call_args.args == ('writetest', kw)


def test_multiples():
    s = Mock()
    DummySubsystemFactory.add_subsystem(s, 'source', cmds,
                                        num_channels=4)
    DummySubsystemFactory.add_subsystem(s.source, 'am',
                                        [['frequency', 'amfreq', 'qty', 'Hz',
                                          {}]])
    DummySubsystemFactory.add_subsystem(s.source, 'source',
                                        cmds, num_channels=2)

    s.device.query.return_value = '4'
    assert 4 * subs.ureg.Hz == s.source[1].frequency_max
    print(s.device.query.call_args.args)

    with pytest.raises(KeyError):
        x = s.source[0].amplitude

    with pytest.raises(KeyError):
        x = s.source[5].shape

    assert 4 * subs.ureg.Hz == s.source[1].am.frequency

    assert 4 * subs.ureg.Hz == s.source[3].source[1].frequency

    assert s.source[1].source[1] is not s.source[2].source[1]

    assert s.source[1].subsystem_idx == 1

    assert s.source[1].source[2].subsystem_idx == 2


def test_repr():
    s = Mock()
    DummySubsystemFactory.add_subsystem(s, 'source', cmds,
                                        num_channels=4)
    DummySubsystemFactory.add_subsystem(s.source, 'am',
                                        cmds)
    assert str(s.source[1]) == 'Source 1'
    print(s.source[1].am)


def test_subsystem_parent():
    s = Mock()
    DummySubsystemFactory.add_subsystem(s, 'source', cmds,
                                        num_channels=4)
    DummySubsystemFactory.add_subsystem(s.source, 'am',
                                        cmds)

    assert s.source[1]._parent() is s
    assert s.source[1].am._parent() is s.source[1]
    assert s.source[2].am._parent() is not s.source[1]
