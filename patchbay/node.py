class Node:
    """A node is a logical unit that may have input and/or output channels.

    Could represent an instrument, algorithm, or collection of nodes.
    """
    def __init__(self, channel_specs=None):
        """Initialize a new Node instance.

        :param channel_specs: dict of channel_id keys with attribute name lists
        """
        if channel_specs:
            self._channel_specs = channel_specs
        else:
            self._channel_specs = {}

    @property
    def channel_ids(self):
        """List the available channel IDs. Read-only property"""
        return list(self._channel_specs.keys())

    def add_channel(self, channel_id, attributes, *, allow_overwrite=False):
        """Add a channel to the node.

        If `allow_overwrite` is True, channels can be overwritten. Otherwise,
        a ValueError is thrown if `ch_id` matches an existing channel ID.

        :param channel_id: ID for the new channel.
        :param attributes: iterable of attribute names for the new channel
        :param allow_overwrite: if True, allow overwriting channels
        """
        if not allow_overwrite and (channel_id in self._channel_specs):
            raise ValueError('Channel ID already exists.')
        self._channel_specs[channel_id] = attributes

    def get_channel(self, channel_id):
        """Get a Channel instance for the channel belonging to this node.

        Throw a KeyError if `channel_id` does not match an existing channel.

        :param channel_id: ID for the desired channel
        :return: Channel
        """
        if channel_id not in self._channel_specs:
            raise KeyError('Channel ID already exists.')
        return Channel(self, channel_id)

    def get_channel_attribute(self, channel_id, attr_name):
        """Get the value of a single channel attribute by name.

        :param channel_id: ID of the channel to query
        :param attr_name: name of the attribute to query
        :return: value of the channel's attribute
        """
        if attr_name not in self._channel_specs[channel_id]:
            raise AttributeError(f"Channel has no attribute '{attr_name}'")

    def describe_channel(self, channel_id, attr_names=None):
        """Get the values of multiple channel attributes.

        If `attr_names` is not provided, return the values for all channel
        attributes.

        :param channel_id: ID of the channel to query
        :param attr_names: iterable of attribute names to query
        :return: dict of attribute names: values
        """
        if attr_names is None:
            attr_names = self._channel_specs[channel_id]
        return {attr: self.get_channel_attribute(channel_id, attr)
                for attr in attr_names}

    def set_channel_attribute(self, channel_id, attr_name, value):
        """Set the value of a single channel attribute by name.

        :param channel_id: ID of the channel to configure
        :param attr_name: name of the attribute to set
        :param value: new value for the attribute
        """
        if attr_name not in self._channel_specs[channel_id]:
            raise AttributeError(f"Channel has no attribute '{attr_name}'")

    def configure_channel(self, channel_id, **kwargs):
        """Set values for multiple channel attributes.

        :param channel_id: ID of the channel to configure
        :param kwargs: attribute names and their values
        """
        if not all([x in self._channel_specs[channel_id]
                    for x in kwargs.keys()]):
            raise AttributeError
        for attr_name, value in kwargs.items():
            self.set_channel_attribute(channel_id, attr_name, value)


class Instrument(Node):
    """An instrument is a node that is associated with a physical device."""
    pass


class Channel:
    """Channel represents a single input or output from a node.

    Channels are just a convenience construct and don't really do any work.
    They should just pass commands up to the node. Should be associated with
    a specific node.
    """
    attributes = ()

    def __init__(self, node, ch_id):
        self._node = node
        self._ch_id = ch_id
        self.attributes = self._node._channel_specs[ch_id]

    def __str__(self):
        return f'{self._node}:{self._ch_id}'

    def __repr__(self):
        return f'{self._node}:{self._ch_id}'

    def __getattr__(self, attr_name):
        if attr_name in self.attributes:
            return self._node.get_channel_attribute(self._ch_id, attr_name)
        else:
            super().__getattribute__(attr_name)

    def __setattr__(self, attr_name, value):
        if attr_name in self.attributes:
            self._node.set_channel_attribute(self._ch_id, attr_name, value)
        else:
            super().__setattr__(attr_name, value)

    def set(self, **kwargs):
        """Set multiple attributes of the channel."""
        pass

    def get(self):
        """Query multiple attributes of the channel."""
        pass
