from patchbay.hardware import scpi
import pytest
from mock import Mock
# from patchbay import node


def test_boolean():
    factory = scpi.ScpiFactory('BooleanClass')
    factory.add_cmd('enabled', 'cmd:subcmd', scpi.scpi_bool())

    s = factory.scpi_class()
    s._parent = Mock(**{'device.query.return_value': '1'})

    s.enabled = True
    assert 'cmd:subcmd 1' == s._parent.device.write.call_args.args[0]
    s.enabled = 0
    assert 'cmd:subcmd 0' == s._parent.device.write.call_args.args[0]

    assert True is s.enabled
    assert 'cmd:subcmd?' == s._parent.device.query.call_args.args[0]


def test_qty():
    factory = scpi.ScpiFactory('QtyClass')
    factory.add_cmd('frequency', 'source1:frequency',
                    scpi.scpi_qty('Hz'),
                    query_keywords=['min', 'max'],
                    write_keywords=['min', 'max', 'default'])
    s = factory.bc()


def test_choices():
    factory = scpi.ScpiFactory('ChoicesClass')
    factory.add_cmd('shape', 'source1:function:shape',
                    scpi.scpi_choice({'sinusoid': 'SIN',
                                      'square': 'SQU'}))
    s = factory.bc()
    assert s.shape == 'square'
    with pytest.raises(KeyError):
        s.shape = 'triangle'
    s.shape = 'sinusoid'
