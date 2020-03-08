import pint
import pytest
from mock import Mock

from patchbay import ureg
from patchbay.hardware import scpi


@pytest.mark.parametrize('cmd_input, cmd_kwds, expected',
                         [(('noarg', 'cmd', None), {}, {'noarg'}),
                          (('normal', 'cmd', scpi.scpi_bool()), {}, {'normal'}),
                          (('wkeywds', 'cmd', scpi.scpi_bool()),
                           {'write_keywords': ['min']},
                           {'wkeywds', 'wkeywds_to_min'}),
                          (('qkeywds', 'cmd', scpi.scpi_num('int')),
                           {'query_keywords': ['max', 'default']},
                           {'qkeywds', 'qkeywds_max', 'qkeywds_default'})
                          ])
def test_property_creation(cmd_input, cmd_kwds, expected):
    subsys = scpi.get_blank_scpi_subsystem('Properties')
    s = subsys()
    d = set(s.__dir__())

    scpi.add_scpi_cmd(subsys, *cmd_input, **cmd_kwds)
    assert expected == set(s.__dir__()).difference(d)


def test_error_converter():
    subsys = scpi.get_blank_scpi_subsystem('ErrorSubsystem')
    scpi.add_scpi_cmd(subsys, 'error', 'system:error', scpi.scpi_error())

    s = subsys()
    s._parent = Mock(**{'device.query.return_value': '+0,"No Error"'})

    assert (0, 'No Error') == s.error

    with pytest.raises(AttributeError):
        s.error = 'bad'  # Can not write errors back to device.


def test_argless_command():
    subsys = scpi.get_blank_scpi_subsystem('ArglessCommand')
    scpi.add_scpi_cmd(subsys, 'clear', 'display:clear', None)

    s = subsys()
    s._parent = Mock()

    s.clear()
    assert 'display:clear' == s._parent.device.write.call_args.args[0]


def test_boolean_converter():
    subsys = scpi.get_blank_scpi_subsystem('BooleanSubsystem')
    scpi.add_scpi_cmd(subsys, 'enabled', 'cmd:subcmd', scpi.scpi_bool())

    s = subsys()
    s._parent = Mock(**{'device.query.return_value': '1'})

    s.enabled = True
    assert 'cmd:subcmd 1' == s._parent.device.write.call_args.args[0]
    s.enabled = False
    assert 'cmd:subcmd 0' == s._parent.device.write.call_args.args[0]
    s.enabled = 1
    assert 'cmd:subcmd 1' == s._parent.device.write.call_args.args[0]
    s.enabled = 0
    assert 'cmd:subcmd 0' == s._parent.device.write.call_args.args[0]

    assert True is s.enabled
    assert 'cmd:subcmd?' == s._parent.device.query.call_args.args[0]


def test_boolean_converter_with_keywords():
    subsys = scpi.get_blank_scpi_subsystem('BooleanSubsystem')
    scpi.add_scpi_cmd(subsys, 'enabled', 'cmd:subcmd', scpi.scpi_bool(),
                      query_keywords=['qmin', 'qmax'], write_keywords=['wkw'])

    s = subsys()
    s._parent = Mock(**{'device.query.return_value': '1'})

    s.enabled = True
    assert 'cmd:subcmd 1' == s._parent.device.write.call_args.args[0]
    s.enabled = False
    assert 'cmd:subcmd 0' == s._parent.device.write.call_args.args[0]

    s.enabled_to_wkw()
    assert 'cmd:subcmd wkw' == s._parent.device.write.call_args.args[0]

    assert True is s.enabled
    assert 'cmd:subcmd?' == s._parent.device.query.call_args.args[0]

    assert True is s.enabled_qmin
    assert 'cmd:subcmd? qmin' == s._parent.device.query.call_args.args[0]
    assert True is s.enabled_qmax
    assert 'cmd:subcmd? qmax' == s._parent.device.query.call_args.args[0]


def test_qty_converter_unit():
    subsys = scpi.get_blank_scpi_subsystem('QtyClass')
    scpi.add_scpi_cmd(subsys, 'frequency', 'cmd:frequency',
                      scpi.scpi_qty('Hz'),
                      query_keywords=['min', 'max'],
                      write_keywords=['min', 'max', 'default'])
    s = subsys()
    s._parent = Mock(**{'device.query.return_value': '500'})

    s.frequency = 100 * ureg.mHz
    assert 'cmd:frequency 0.1' == s._parent.device.write.call_args.args[0]

    s._parent.reset_mock()
    with pytest.raises(pint.errors.DimensionalityError):
        s.frequency = 234 * ureg.m
    s._parent.device.write.assert_not_called()

    with pytest.raises(ValueError):
        s.frequency = 234
    s._parent.device.write.assert_not_called()

    assert 500 * ureg.Hz == s.frequency
    assert 'cmd:frequency?' == s._parent.device.query.call_args.args[0]


def test_choices_converter():
    subsys = scpi.get_blank_scpi_subsystem('ChoicesClass')
    scpi.add_scpi_cmd(subsys, 'shape', 'cmd:shape',
                      scpi.scpi_choice({'sinusoid': 'SIN',
                                        'square': 'SQU'}))
    s = subsys()
    s._parent = Mock(**{'device.query.return_value': 'SQU'})

    s.shape = 'sinusoid'
    assert 'cmd:shape SIN' == s._parent.device.write.call_args.args[0]

    assert s.shape == 'square'
    assert 'cmd:shape?' == s._parent.device.query.call_args.args[0]

    with pytest.raises(KeyError):
        s.shape = 'triangle'
