import pytest

from patchbay.node import Channel
from pytest_util import MockNode
# noinspection PyUnresolvedReferences
from pytest_util import node


@pytest.fixture
def blank_node():
    return MockNode()


def test_node(blank_node):
    """Check that node loads and has no channels."""
    assert not blank_node.channel_ids


def test_channel_ids(node):
    """Check that node correctly reports the existing channel IDs"""
    assert {'b', 0, (1, 'c')} == set(node.channel_ids)


def test_add_channels(blank_node):
    """Check ability to add channels to a node."""
    blank_node.add_channels({0: ['attr1']})  # add single channel 0

    assert 0 in blank_node.channel_ids  # the channel id is found
    assert {'attr1'} == blank_node.channel_specs[0]  # the attr list matches

    blank_node.add_channels({(0, 'hello'): ['attr1', 'attr2', 'attr3'],
                             'ch_D': ['attrA', 'attrB']})
    assert 0 in blank_node.channel_ids  # this channel should still exist

    assert (0, 'hello') in blank_node.channel_ids  # new channel added
    assert {'attr1', 'attr2', 'attr3'} == blank_node.channel_specs[(0, 'hello')]

    assert 'ch_D' in blank_node.channel_ids
    assert {'attrA', 'attrB'} == blank_node.channel_specs['ch_D']


def test_add_channels_duplicate(blank_node):
    """Check for appropriate errors when adding duplicate channel IDs"""
    blank_node.add_channels({'a': []})
    assert set() == blank_node.channel_specs['a']

    # try adding a single channel that clashes
    with pytest.raises(ValueError):  # overwriting throws an error
        blank_node.add_channels({'a': ['attr1']})
    assert set() == blank_node.channel_specs['a']  # no change to channel

    #  overwriting is allowed if the flag is set
    blank_node.add_channels({'a': ['attrA']}, allow_overwrite=True)
    assert {'attrA'} == blank_node.channel_specs['a']

    #  try adding multiple channels, one of which clashes
    with pytest.raises(ValueError):  # overwriting throws an error
        blank_node.add_channels({'b': ['attrB'], 'a': ['attr1']})
    assert {'attrA'} == blank_node.channel_specs['a']  # no change to channel
    assert 'b' not in blank_node.channel_specs  # channel is not added

    #  overwriting is allowed if the flag is set
    blank_node.add_channels({'a': ['attr1'], 'b': ['attrB']},
                            allow_overwrite=True)
    assert {'attr1'} == blank_node.channel_specs['a']  # channel is updated
    assert {'attrB'} == blank_node.channel_specs['b']  # channel is added


def test_get_channel(node):
    """Check getting a Channel instance from a node."""
    # get a channel with simple name
    ch = node.get_channel(0)  # get an existing Channel
    assert isinstance(ch, Channel)

    # get a channel with tuple name
    ch = node.get_channel((1, 'c'))
    assert isinstance(ch, Channel)

    with pytest.raises(KeyError):  # raise a KeyError if channel does not exist
        node.get_channel('dne')


def test_get_channel_attribute(node):
    """Node base class only checks for attribute existence."""
    assert 4 == node.get_channel_attribute(0, 'n0_0')
    assert False == node.get_channel_attribute((1, 'c'), 'n1c_0')

    with pytest.raises(AttributeError):
        node.get_channel_attribute('b', 'nope')


def test_describe_channel(node):
    # if attr_names not specified, return values for all attributes
    assert {'n0_0': 4} == node.describe_channel(0)
    assert {'n0_0': 4} == node.describe_channel(0, {})
    assert {'b_0': 0x3, 'b_1': 'b1val'} == node.describe_channel('b')

    # only return values for requested attributes
    assert 'b1val' == node.describe_channel('b', ['b_1'])

    # raise AttributeError if the attribute name is not valid
    with pytest.raises(AttributeError):
        node.describe_channel((1, 'c'), ['nope'])

    # raise KeyError is the channel ID is not valid
    with pytest.raises(KeyError):
        node.describe_channel(('f', 12), ['nope'])


def test_set_channel_attribute(node):
    """Node base class only checks for attribute existence."""
    node.set_channel_attribute('b', 'b_1', 23)
    assert 23 == node.get_channel_attribute('b', 'b_1')

    node.set_channel_attribute((1, 'c'), 'n1c_1', 'HelloWorld')
    assert 'HelloWorld' == node.get_channel_attribute((1, 'c'), 'n1c_1')

    with pytest.raises(AttributeError):
        node.set_channel_attribute(0, 'nope', None)


def test_configure_channel(node):
    # if any attributes are incorrect, nothing should get configured
    with pytest.raises(AttributeError):
        node.configure_channel('b', b_4=22)
    assert 'b_4' not in node.channel_specs['b']
    assert node.call_counts['set_channel_attribute'] == 0

    with pytest.raises(AttributeError):
        node.configure_channel('b', b_0=4, b_4=None)
    assert 0x3 == node.get_channel_attribute('b', 'b_0')
    assert node.call_counts['set_channel_attribute'] == 0

    # if all attributes are correct, the set method should be called for each
    node.configure_channel(0, n0_0=2)
    assert 2 == node.get_channel_attribute(0, 'n0_0')
    assert node.call_counts['set_channel_attribute'] == 1

    node.call_counts.clear()
    node.configure_channel((1, 'c'), n1c_1=5, n1c_0=9)
    assert ({'n1c_0': 9, 'n1c_1': 5, 'n1c_2': '1c2val'}
            == node.describe_channel((1, 'c')))
    assert node.call_counts['set_channel_attribute'] == 2

    # raise KeyError is the channel ID is not valid
    with pytest.raises(KeyError):
        node.configure_channel(('f', 12), nope=8)
