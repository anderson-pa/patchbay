# noinspection PyUnresolvedReferences
from pytest_util import node


def test_representations(node):
    """Check the string and repr results."""
    ch = node.get_channel(0)
    assert 'Channel<MockNode:0>' == str(ch)
    assert 'Channel<MockNodeRepr:0>' == repr(ch)

    ch = node.get_channel('b')
    assert 'Channel<MockNode:b>' == str(ch)
    assert 'Channel<MockNodeRepr:b>' == repr(ch)

    ch = node.get_channel((1, 'c'))
    assert "Channel<MockNode:(1, 'c')>" == str(ch)
    assert "Channel<MockNodeRepr:(1, 'c')>" == repr(ch)


def test_get(node):
    # Channel.get method returns all attribute values if none are specified,
    # otherwise returns only the values requested
    ch = node.get_channel(0)
    assert {'n0_0': 4} == ch.get()
    assert 4 == ch.get('n0_0')

    ch = node.get_channel('b')
    assert {'b_0': 0x3, 'b_1': 'b1val'} == ch.get()
    assert 'b1val' == ch.get('b_1')
    assert {'b_0': 0x3, 'b_1': 'b1val'} == ch.get('b_1', 'b_0')


def test_get_by_attribute(node):
    # Channel.get method returns all attribute values if none are specified,
    # otherwise returns only the values requested
    ch = node.get_channel(0)
    assert 4 == ch.n0_0

    ch = node.get_channel('b')
    assert 0x3 == ch.b_0
    assert 'b1val' == ch.b_1


def test_set(node):
    ch = node.get_channel(0)
    ch.set(n0_0='pretzel')
    assert 'pretzel' == ch.get('n0_0')

    ch = node.get_channel((1, 'c'))
    ch.set(n1c_0=12, n1c_2=False, n1c_1='jinkies')
    assert {'n1c_0': 12, 'n1c_1': 'jinkies', 'n1c_2': False} == ch.get()


def test_set_by_attribute(node):
    ch = node.get_channel(0)
    ch.n0_0 = 'pretzel'
    assert 'pretzel' == ch.get('n0_0')

    ch = node.get_channel((1, 'c'))
    ch.n1c_1 = False
    assert {'n1c_0': False, 'n1c_1': False, 'n1c_2': '1c2val'} == ch.get()

    # assignment of new python attributes is not broken
    ch.dne = 'not in list'
    assert 'not in list' == ch.dne
