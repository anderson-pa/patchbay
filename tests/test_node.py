import pytest

from patchbay.node import Node, Channel
from pytest_util import counted


@pytest.fixture
def blank_node():
    return Node()


@pytest.fixture
def node():
    node = Node()
    node._channel_specs = {'a': ['a_attr'],
                           'b': ['b_attr1', 'b_attr2'],
                           (0, 'c'): ['c_attr1', 'c_attr2']}
    return node


@pytest.fixture()
def channel(node):
    return node.get_channel('b')


def test_node(blank_node):
    """Check that node loads and has no channels."""
    assert not blank_node.channel_ids


def test_channel_ids(node):
    """Check that node correctly reports the existing channel IDs"""
    assert {'b', 'a', (0, 'c')} == set(node.channel_ids)


def test_add_channel(blank_node):
    """Check ability to add channels to a node."""
    blank_node.add_channel(0, ['attr1'])  # add channel 0

    assert 0 in blank_node.channel_ids  # the channel id is found
    assert ['attr1'] == blank_node._channel_specs[0]  # the attr list matches


def test_add_channel_duplicate(blank_node):
    """Check for appropriate errors when adding duplicate channel IDs"""
    blank_node.add_channel('a', [])
    assert [] == blank_node._channel_specs['a']

    with pytest.raises(ValueError):  # overwriting throws an error
        blank_node.add_channel('a', [])
    assert [] == blank_node._channel_specs['a']  # no change to channel

    #  overwriting is allowed if the flag is set
    blank_node.add_channel('a', ['attr1'], allow_overwrite=True)
    assert ['attr1'] == blank_node._channel_specs['a']


def test_get_channel(node):
    """Check getting a Channel instance from a node."""
    # get a channel with simple name
    ch = node.get_channel('a')  # get an existing Channel
    assert isinstance(ch, Channel)

    # get a channel with tuple name
    ch = node.get_channel((0, 'c'))
    assert isinstance(ch, Channel)

    with pytest.raises(KeyError):  # raise a KeyError if channel does not exist
        node.get_channel('dne')


def test_get_channel_attribute(node):
    """Node base class only checks for attribute existence."""
    node.get_channel_attribute('a', 'a_attr')
    node.get_channel_attribute((0, 'c'), 'c_attr1')

    with pytest.raises(AttributeError):
        node.get_channel_attribute('b', 'nope')


def test_describe_channel(node):
    # if attr_names not specified, return values for all attributes
    assert {'a_attr': None} == node.describe_channel('a')
    assert {'b_attr1': None, 'b_attr2': None} == node.describe_channel('b')

    # only return values for requested attributes
    assert {'b_attr2': None} == node.describe_channel('b', ['b_attr2'])

    # raise AttributeError if the attribute name is not valid
    with pytest.raises(AttributeError):
        node.describe_channel((0, 'c'), ['nope'])


def test_set_channel_attribute(node):
    """Node base class only checks for attribute existence."""
    node.set_channel_attribute('b', 'b_attr2', None)
    node.set_channel_attribute((0, 'c'), 'c_attr2', None)

    with pytest.raises(AttributeError):
        node.set_channel_attribute('a', 'nope', None)


def test_configure_channel(node):
    # wrap the set_channel_attribute method so calls can be counted
    node.set_channel_attribute = counted(node.set_channel_attribute)

    # if any attributes are incorrect, nothing should get configured
    with pytest.raises(AttributeError):
        node.configure_channel('b', b_attr4=None)
    assert node.set_channel_attribute.calls == 0

    with pytest.raises(AttributeError):
        node.configure_channel('b', b_attr1=4, b_attr4=None)
    assert node.set_channel_attribute.calls == 0

    # if all attributes are correct, the set method should be called for each
    node.configure_channel('a', a_attr=2)
    assert node.set_channel_attribute.calls == 1

    node.configure_channel((0, 'c'), c_attr2=5, c_attr1=9)
    assert node.set_channel_attribute.calls == 3
