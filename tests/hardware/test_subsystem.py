import pytest
from mock import Mock

from patchbay.hardware.subsystem import (SubsystemFactory, ValueConverter,
                                         add_can_querywrite_keywords)


@add_can_querywrite_keywords
def convert_identity(_):
    """Get a converter for passing along whatever is given.

    :param _: dummy for signature matching
    :return: ValueConverter for anything
    """
    return ValueConverter(lambda x: x, lambda y: y)


function_shapes = {'sinusoid': 'SIN',
                   'square': 'SQU',
                   'triangle': 'TRI',
                   'ramp': 'RAMP',
                   'noise': 'NOIS',
                   'custom': 'USER',
                   }

choice_map = {'shape': function_shapes,
              'amplitude_unit': {'Vpp': 'VPP',
                                 'Vrms': 'VRMS',
                                 'dBm': 'DBM'},
              }


class DummySubsystemFactory(SubsystemFactory):
    converter_map = {name: convert_identity
                     for name in ['error', 'bool', 'qty', 'choice']}

    def __init__(self, prototype_name):
        self.prototype_name = prototype_name

    def __call__(self, prototype_name, *args, **kwargs):
        self.prototype_name = prototype_name

    @staticmethod
    def query_func(name, converter, keyword=None):
        return _cmd(name, keyword, is_query=True)

    @staticmethod
    def write_func(name, converter, keyword=None):
        return _cmd(name, keyword, is_query=False)

    @staticmethod
    def hook_get_new_subsystem(new_subsystem):
        new_subsystem.scpi = 'scpi_string'


def _cmd(command, keyword, is_query):
    keyword = '_' + keyword if keyword else ''

    def q_func(self):
        try:
            print(f'index is: {self.idx}')
        except AttributeError:
            print('no index')
        return f'Query: {command}{keyword}'

    def w_func(self, val=None):
        try:
            print(f'index is: {self.idx}')
        except AttributeError:
            print('no index')
        print(f'Write: {command}{keyword}: {val}')

    return q_func if is_query else w_func


def test_make_dummy():
    s = Mock()
    DummySubsystemFactory.add_subsystem('source', s, choice_map)
    DummySubsystemFactory.add_subsystem('amplitude_modulation', s.source,
                                        choice_map)
    print(s.source.frequency)
    s.source.frequency = 2
    s.source.am.frequency = 4

    print(s.source.scpi)


def test_multiples():
    s = Mock()
    DummySubsystemFactory.add_subsystem(s, 'source', choice_maps=choice_map,
                                        num_channels=4)
    DummySubsystemFactory.add_subsystem(s.source, 'amplitude_modulation',
                                        choice_maps=choice_map)
    DummySubsystemFactory.add_subsystem(s.source, 'source',
                                        choice_maps=choice_map, num_channels=2)

    print(s.source[1].frequency)

    with pytest.raises(KeyError):
        print(s.source[0].amplitude)

    with pytest.raises(KeyError):
        print(s.source[5].shape)

    print(s.source[1].am.frequency)

    print(s.source[3].source[1].frequency)

    assert s.source[1].source[1] is not s.source[2].source[1]

    assert s.source[1].channel_idx == 1

    assert s.source[1].source[2].channel_idx == 2


def test_repr():
    s = Mock()
    DummySubsystemFactory.add_subsystem(s, 'source', choice_maps=choice_map,
                                        num_channels=4)
    DummySubsystemFactory.add_subsystem(s.source, 'amplitude_modulation',
                                        choice_maps=choice_map)
    print(s.source)
    print(s.source[1].am)