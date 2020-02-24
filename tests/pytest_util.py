from collections import Counter
from functools import wraps

import pytest

from patchbay.node import Node


def count(f):
    """Decorator for MockNode to count function calls."""

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        self.call_counts[f.__name__] += 1
        return f(self, *args, **kwargs)

    return wrapper


class MockNode(Node):
    """Node subclass for testing.

    Node and channel attributes are simply stored/retrieved using dicts.
    """

    def __init__(self):
        self.call_counts = Counter()
        self.data = {}

        channel_specs = {}
        super().__init__(channel_specs)

    def __str__(self):
        return 'MockNode'

    def __repr__(self):
        return 'MockNodeRepr'

    def add_channel(self, channel_id, attributes, *, allow_overwrite=False):
        super().add_channel(channel_id, attributes,
                            allow_overwrite=allow_overwrite)
        self.data[channel_id] = {a: None for a in attributes}

    @count
    def get_channel_attribute(self, channel_id, attr_name):
        super().get_channel_attribute(channel_id, attr_name)
        return self.data[channel_id][attr_name]

    @count
    def set_channel_attribute(self, channel_id, attr_name, value):
        super().set_channel_attribute(channel_id, attr_name, value)
        self.data[channel_id][attr_name] = value


@pytest.fixture
def node():
    """A simple MockNode with dummy data for testing."""
    node = MockNode()
    node.channel_specs = {0: ['n0_0'],
                          'b': ['b_0', 'b_1'],
                          (1, 'c'): ['n1c_0', 'n1c_1', 'n1c_2']}
    node.data = {0: {'n0_0': 4},
                 'b': {'b_0': 0x3, 'b_1': 'b1val'},
                 (1, 'c'): {'n1c_0': False, 'n1c_1': 3.14, 'n1c_2': '1c2val'}}
    return node
