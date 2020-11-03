import json
import weakref
from collections import namedtuple
from functools import wraps
from os import path

_defs_file = path.join(path.dirname(__file__), 'subsystem_definitions.json')
with open(_defs_file, 'r') as fp:
    prototype_definitions = json.load(fp)

for _, subsystem_def in prototype_definitions.items():
    for cmd in subsystem_def['commands']:
        # separate choices from a string to a list
        if cmd[1] == 'choice':
            cmd[2] = [arg.strip() for arg in cmd[2].split(',')]

        # separate keywords from strings to a list if present
        try:
            for kw in ['query_keywords', 'write_keywords']:
                try:
                    cmd[3][kw] = [key.strip() for key in cmd[3][kw].split(',')]
                except KeyError:
                    pass
        except IndexError:
            pass

ValueConverter = namedtuple('ValueConverter', 'query, write')


def add_can_querywrite_keywords(func):
    """Decorator for ValueConverter functions to add query/write keywords

    :param func: function to decorate
    :return: decorated function with can_query and can_write as keywords
    """

    @wraps(func)
    def wrapped(*args, can_query=True, can_write=True, **kwargs):
        converter = func(*args, **kwargs)
        return ValueConverter(converter.query if can_query else None,
                              converter.write if can_write else None)

    # add the keywords to the docstring
    can_qw_doc_str = (':param can_query: if True, add a query converter\n    '
                      ':param can_write: if True, add a write converter\n    ')

    doc_return_pos = wrapped.__doc__.find(':return:')
    if doc_return_pos > -1:
        wrapped.__doc__ = (wrapped.__doc__[:doc_return_pos]
                           + can_qw_doc_str + wrapped.__doc__[doc_return_pos:])
    return wrapped


class SubsystemFactory:
    converter_map = {name: None
                     for name in ['error', 'bool', 'qty', 'choice']}

    @classmethod
    def add_subsystem(cls, target, name=None, *, prototype=None,
                      choice_maps=None, num_channels=1, zero_indexed=False):
        """Get a class definition for the requested subsystem.

        :param target: instance to add the subsystem to
        :param name: name of the subsystem to add
        :param prototype: alternate subsystem prototype to use if not standard
        :param choice_maps: mappings for any choice commands
        :param num_channels: if indexed, how many channels to create
        :param zero_indexed: if True, the first channel will be 0 instead of 1
        """
        if not prototype:
            prototype = prototype_definitions[name]

        subsystem = cls._get_new_subsystem(prototype['name'],
                                           prototype['description'])
        cls.add_cmds(prototype, subsystem, choice_maps)

        # if the target is actually multiple channels, apply to each one
        if isinstance(target, SubSystemDict):
            targets = [t for t in target.values()]
        else:
            targets = [target]

        for t in targets:
            # if indexed, wrap with a custom dictionary
            if prototype.get('indexed'):
                start_index = 0 if zero_indexed else 1
                ch_ids = [i + start_index for i in range(num_channels)]
                channels = SubSystemDict({c: subsystem(t, channel_idx=c)
                                          for c in ch_ids})
                setattr(t, prototype['name'], channels)
            else:
                setattr(t, prototype['name'], subsystem(t))

    @classmethod
    def graft_subsystem(cls, name, target):
        """Add subsystem properties and methods to the given target.

        :param name: name of the subsystem to add
        :param target: class to add commands to.
        """
        prototype = prototype_definitions[name]
        cls.add_cmds(prototype, target)

    @classmethod
    def add_cmds(cls, prototype, target, choice_maps=None):
        """Add commands to target from the prototype definition.

        Prototype is a dictionary with the keys: name, description, iterable,
        commands, subsystems.

        Each command definition is an iterable with elements: name,
        converter_type, converter_arg, kwargs

        todo: full writeup of the format once this has been refined.

        :param prototype: definition of the subsystem commands
        :param target: class to add commands to.
        """
        if not choice_maps:
            choice_maps = {}

        for cmd_name, cmd_type, cmd_arg, *cmd_kwargs in prototype['commands']:
            if cmd_type == 'choice':
                choice_map = choice_maps[cmd_name]
                cmd_arg = {key: val for key, val in choice_map.items()
                           if key in cmd_arg}

            if not cmd_kwargs:
                cmd_kwargs = {}
            else:
                cmd_kwargs = cmd_kwargs[0]

            cls.add_cmd(target, cmd_name, cmd_type, cmd_arg, **cmd_kwargs)

    @classmethod
    def add_cmd(cls, target, name, cmd_type, cmd_arg=None, *,
                can_query=True, can_write=True,
                query_keywords=None, write_keywords=None):
        """Add command parameters and methods to a class.

        Add properties and methods associated with `name` to `target`,
        which is generally a subsystem class. These properties and methods
        use the converter functions as pre-/post- processors to translate
        values between Python and the device:

            Query -> query_converter(query_cmd())
            Write -> write_cmd(write_converter(value))

        If the command is query and write accessible, a property is added. A
        get/set method is used if only query or write is allowed. Otherwise, an
        unadorned method is added. So:

            QW -> target.name [= value]
            Q. -> target.get_name()
            .W -> target.set_name(value)
            .. -> target.name()

        Query/Write access is defined by the keywords 'can_query/write'
        combined with existence of the corresponding converter. For example,
        if `can_write` is False or converter.write is None, the command is
        not writable.

        If keywords are included, additional properties are added for each:
        `target.name_qkeyword()` and `target.name_to_wkeyword()`. This allows
        for commands that have e.g., min, max, or default values.

        The different converters allow for more customization, including
        boolean conversions, enforcing units on quantities, and setting a
        list of choices.

        An additional method is added for choice converters that returns a
        list of the allowed choices: `target.name_choices()`

        :param target: class where the commands will be added
        :param fullname: full lookup name for the attributes and methods
        :param cmd_type: ValueConverter specific for device and argument
        :param cmd_arg: argument passed to converter constructor, if any
        :param can_query: if True, a query property is added
        :param can_write: if True, a write property is added
        :param query_keywords: additional query keywords for this command
        :param write_keywords: additional write keywords for this command
        """
        if cmd_type == 'choice':
            setattr(target, f'{name}_choices',
                    staticmethod(lambda: tuple(cmd_arg.keys())))

        c_func = cls.converter_map[cmd_type]
        converter = c_func(cmd_arg, can_query=can_query, can_write=can_write)

        # set the property or function
        if all(converter):
            # write a property
            prop_get = cls.query_func(name, converter.query)
            prop_set = cls.write_func(name, converter.write)
            setattr(target, name, property(prop_get, prop_set))
        else:
            if converter.query is not None:
                # only a query converter so create a get method
                setattr(target, 'get_' + name,
                        cls.query_func(name, converter.query))
            else:
                # if only a write converter, create a get method
                # if neither, its a plain command with no inputs
                w_prefix = 'set_' if converter.write is not None else ''
                setattr(target, w_prefix + name,
                        cls.write_func(name, converter.write))

        # set additional properties for the keywords
        if query_keywords is None:
            query_keywords = []
        for key in query_keywords:
            setattr(target, f'{name}_{key}',
                    property(cls.query_func(name, converter.query, key)))

        if write_keywords is None:
            write_keywords = []
        for key in write_keywords:
            setattr(target, f'{name}_to_{key}',
                    cls.write_func(name, None, key))

    @staticmethod
    def query_func(name, converter, keyword=None):
        raise NotImplementedError

    @staticmethod
    def write_func(name, converter, keyword=None):
        raise NotImplementedError

    @classmethod
    def _get_new_subsystem(cls, name, description=None):
        """Create a new, blank class to build upon.

        :param name: name of the class
        :param description: docstring description
        :return: class
        """

        new_subsystem = type(name.capitalize(), (object,), {})
        new_subsystem.__init__ = subsystem_init
        new_subsystem.__doc__ = description
        new_subsystem.__repr__ = subsystem_repr(name.capitalize())
        new_subsystem._device = _device

        cls.hook_get_new_subsystem(new_subsystem)
        return new_subsystem

    @staticmethod
    def hook_get_new_subsystem(new_subsystem):
        """Method to allow subclasses to add commands during init."""
        pass


def subsystem_init(self, parent, channel_idx=None):
    self._parent = weakref.ref(parent)
    self.channel_idx = channel_idx


def subsystem_repr(name):
    def repr(self):
        if self.channel_idx:
            return name + str(self.channel_idx)
        else:
            return name

    return repr


def _device(self):
    return self._parent().device


class SubSystemDict(dict):
    """Simple subclass of a dictionary.

    This is used to hold multiple subsystem channels. A simple dict won't do
    because it does not allow other attributes or methods to be added.
    """

    def __init__(self, *args):
        dict.__init__(self, *args)

    def rename_channel(self, old_key, new_key):
        self[new_key] = self.pop(old_key)
