from patchbay.hardware import scpi
import pytest
from mock import Mock
import pint
from patchbay import ureg


def test_boolean():
    subsys = scpi.get_blank_scpi_subsystem('BooleanSubsystem')
    scpi.add_scpi_cmd(subsys, 'enabled', 'cmd:subcmd', scpi.scpi_bool())

    s = subsys()
    s._parent = Mock(**{'device.query.return_value': '1'})

    s.enabled = True
    assert 'cmd:subcmd 1' == s._parent.device.write.call_args.args[0]
    s.enabled = 0
    assert 'cmd:subcmd 0' == s._parent.device.write.call_args.args[0]

    assert True is s.enabled
    assert 'cmd:subcmd?' == s._parent.device.query.call_args.args[0]


def test_qty():
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


def test_choices():
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

