import builtins
import weakref
from collections import namedtuple
from functools import wraps, lru_cache
from types import MappingProxyType

from pint import DimensionalityError

from patchbay import ureg
from patchbay.node import Node

# _defs_file = path.join(path.dirname(__file__), 'subsystem_definitions.json')
# with open(_defs_file, 'r') as fp:
#     prototype_definitions = json.load(fp)

# for _, subsystem_def in prototype_definitions.items():
#     for cmd in subsystem_def['commands']:
#         # separate choices from a string to a list
#         if cmd[1] == 'choice':
#             cmd[2] = [arg.strip() for arg in cmd[2].split(',')]
#
#         # separate keywords from strings to a list if present
#         try:
#             for kw in ['query_keywords', 'write_keywords']:
#                 try:
#                     cmd[3][kw] = [key.strip() for key in cmd[3][kw].split(',')]
#                 except KeyError:
#                     pass
#         except IndexError:
#             pass

ValueConverter = namedtuple('ValueConverter', 'query, write')
CmdDef = namedtuple('CommandDefinition',
                    'name, cmd, cmd_type, cmd_arg, cmd_kwargs',
                    defaults=(None, MappingProxyType({})))


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


@add_can_querywrite_keywords
def convert_bool(_=None):
    """Get a converter for booleans.

    Booleans are written to the device as 0/1 typically, so convert to int.
    Queries typically return 0/1 as a string, so convert to int and then
    boolean.

    :param _: placeholder for signature matching to other converter functions
    :return: ValueConverter for booleans
    """
    return ValueConverter(lambda v: bool(int(v)), int)


@add_can_querywrite_keywords
def convert_num(dtype):
    """Get a converter for unit-less numbers.

    This converter is dumb and maybe not necessary.

    :param dtype: name of type to convert to (e.g. 'int', 'float')
    :return: ValueConverter for nums
    """
    return ValueConverter(getattr(builtins, dtype), lambda v: v)


@lru_cache()  # don't create multiple functions for the same conversion
def qty_query_converter(unit_str):
    """Get a query converter function for quantities.

    Return a function that converts an input value to a quantity with the
    given base unit.

    :param unit_str: string representation of the unit for this converter
    :return: function for quantity query conversions.
    """

    def query_converter(value):
        """Return the value as a quantity with units of {unit}

        :param value: value returned by the query
        :return: value as a quantity with units of {unit}
        """
        return float(value) * ureg(unit_str)

    query_converter.__doc__ = str(query_converter.__doc__).format(unit=unit_str)
    return query_converter


@lru_cache()  # don't create multiple functions for the same conversion
def qty_write_converter(unit_str):
    """Get a write converter function for quantities.

    Return a function that converts an input quantity value to the magnitude
    in the given base unit. The returned function will raises a ValueError if
    the input value is not a pint quantity.

    :param unit_str: string representation of the unit for this converter
    :return: function for quantity write conversions.
    """

    def write_converter(quantity):
        """Return the magnitude of quantity in terms of {unit}

        :param quantity: pint quantity
        :return: magnitude in terms of {unit}
        """
        try:
            base_unit_value = quantity.to(ureg(unit_str))
        except AttributeError:
            raise DimensionalityError(unit_str, None)
        return base_unit_value.magnitude

    write_converter.__doc__ = str(write_converter.__doc__).format(unit=unit_str)
    return write_converter


def value_to_percent(v):
    return v * 100


def value_from_percent(v):
    return float(v) / 100


@add_can_querywrite_keywords
def convert_qty(unit_str):
    """Get a converter for quantities.

    Generate a converter to send and recieve unit-aware quantities to a
    device. Values sent to the device only need to have the right
    dimensionality so that pint can convert to the unit that the device
    expects.

    This uses the base unit without SI prefixes to avoid possible order or
    magnitude errors. As an example, SCPI is case-insensitive and so `milli`
    and `Mega` are ambiguous with one usually assumed over the other.

    Percentages could be converted to dimensionless pint quantities but for
    now just treated as regular floats. Not clear that the extra overhead is
    useful.

    :param unit_str: string representation of the unit for this command
    :return: ValueConverter for quantities
    """
    if unit_str == '%':
        converter = ValueConverter(value_from_percent, value_to_percent)
    else:
        converter = ValueConverter(qty_query_converter(unit_str),
                                   qty_write_converter(unit_str))
    return converter


@add_can_querywrite_keywords
def convert_choice(choices):
    """Get a converter for choice lists.

    Some commands allow a restricted set of choices (essentially an enum).
    Use a list if the keywords for the instrument and the Python interface
    should be the same. Otherwise pass a dictionary with Python names for the
    keys and instrument names for the values.

    :param choices: list or dict of choice options
    :return: ValueConverter for a list of choices
    """
    try:
        inv_choices = {v: k for k, v in choices.items()}
    except AttributeError:
        inv_choices = choices

    return ValueConverter(lambda v: inv_choices[v], lambda v: choices[v])


class HardwareNode(Node):
    """An instrument is a node that is associated with a physical device."""

    def __init__(self, device):
        super().__init__()
        self.device = device
        self.make = ''
        self.model = ''
        self.serial = ''
        self.versions = {}


class SubsystemFactory:
    converters = {}

    @classmethod
    def get_converter(cls, name):
        converter = None
        try:
            converter = cls.converters[name]
        except KeyError:
            converter = {'bool': convert_bool,
                         'choice': convert_choice,
                         'number': convert_num,
                         'qty': convert_qty,
                         }[name]
        return converter

    @classmethod
    def add_subsystem(cls, target, name, commands,
                      description=None, num_channels=None, zero_indexed=False,
                      ):
        """Get a class definition for the requested subsystem.

        :param target: instance to add the subsystem to
        :param name: name of the subsystem to add
        :param commands: list of commands (CmdDefs) to add to the subsystem
        :param description: string describing the subsystem
        :param num_channels: how many channels to create or None if not indexed
        :param zero_indexed: if True, the first channel will be 0 instead of 1
        """
        subsystem = cls._get_new_subsystem(name, description)
        cls.add_cmds(subsystem, commands)

        # if the target is actually multiple channels, apply to each one
        if isinstance(target, SubSystemDict):
            targets = [t for t in target.values()]
        else:
            targets = [target]

        for t in targets:
            # if indexed, wrap with a custom dictionary
            if num_channels is not None:
                start_index = 0 if zero_indexed else 1
                ch_ids = [i + start_index for i in range(num_channels)]
                channels = SubSystemDict({c: subsystem(t, idx=c)
                                          for c in ch_ids})
                setattr(t, name, channels)
            else:
                setattr(t, name, subsystem(t))
        return subsystem

    @classmethod
    def add_cmds(cls, target, command_definitions):
        """Add commands to target from command definitions.

        `command_definitions` is a list of `CmdDefs` (or compatible lists),
        each with the following items:

        * name: base name of the command
        * cmd: command function or syntax (SubClass specific usage)
        * cmd_type: error, bool, qty, choice, or user defined type
        * cmd_arg: any args associated with the command type
        * cmd_kwargs: modifiers and keywords for the commands

        :param target: class to add commands to.
        :param command_definitions: list of CmdDefs
        """
        for c in command_definitions:
            *args, kwargs = CmdDef(*c)
            cls.add_cmd(target, *args, **kwargs)

    @classmethod
    def add_cmd(cls, target, name, cmd, cmd_type, cmd_arg=None, *,
                can_query=True, can_write=True, split_cmd=False,
                query_keywords=None, write_keywords=None):
        """Add command properties and methods to a class.

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
        :param name: base name for the attributes and methods
        :param cmd: command function or syntax (SubClass specific usage)
        :param cmd_type: ValueConverter specific for device and argument
        :param cmd_arg: argument passed to converter constructor, if any
        :param can_query: if True, a query property is added
        :param can_write: if True, a write property is added
        :param split_cmd: True if separate commands are needed (currently only
            implemented for bool write)
        :param query_keywords: additional query keywords for this command
        :param write_keywords: additional write keywords for this command
        """
        # modify the class itself if target is an instance
        if not isinstance(target, type):
            target = target.__class__

        # for choice types, add a method to list the choices
        if cmd_type == 'choice':
            setattr(target, f'{name}_choices',
                    staticmethod(lambda: tuple(cmd_arg.keys())))

        c_func = cls.get_converter(cmd_type)
        converter = c_func(cmd_arg, can_query=can_query, can_write=can_write)

        # set the property or function
        if all(converter):
            # write a property
            prop_get = cls.query_func(cmd, converter.query)
            prop_set = cls.write_func(cmd, converter.write)
            setattr(target, name, property(prop_get, prop_set))
        elif converter.query is not None:
            # only a query converter so create a get method unless a write
            # method already exists
            prop_get = cls.query_func(cmd, converter.query)
            if hasattr(target, f'set_{name}'):
                prop_set = getattr(target, f'set_{name}')
                setattr(target, name, property(prop_get, prop_set))
                delattr(target, f'set_{name}')
            else:
                setattr(target, f'get_{name}', prop_get)
        elif converter.write is not None:
            # only a write converter so create a set method unless a query
            # method already exists

            # if cmds are split (only supported for bool type for now)
            if split_cmd:
                setters = {key: cls.write_func(c, None, '')
                           for key, c in zip([True, False], cmd)}
                prop_set = lambda s, x: setters[x](s)
            else:
                prop_set = cls.write_func(cmd, converter.write)

            if hasattr(target, f'get_{name}'):
                prop_get = getattr(target, f'get_{name}')
                setattr(target, name, property(prop_get, prop_set))
                delattr(target, f'get_{name}')
            else:
                setattr(target, f'set_{name}', prop_set)
        else:
            # if neither query nor write converter, add simple command
            setattr(target, name, cls.write_func(cmd, converter.write))

        # set additional properties for the keywords
        if query_keywords is None or not can_query:
            query_keywords = []
        for key in query_keywords:
            setattr(target, f'{name}_{key}',
                    property(cls.query_func(cmd, converter.query, key)))

        if write_keywords is None or not can_write:
            write_keywords = []
        for key in write_keywords:
            setattr(target, f'{name}_to_{key}',
                    cls.write_func(cmd, None, key))

    @staticmethod
    def query_func(command, converter, keyword=None):
        raise NotImplementedError

    @staticmethod
    def write_func(command, converter, keyword=None):
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
        new_subsystem.subsystem_type = name.capitalize()
        new_subsystem.__doc__ = description
        new_subsystem.__repr__ = subsystem_repr
        setattr(new_subsystem, 'device', property(subsystem_get_device, None))

        cls.hook_get_new_subsystem(new_subsystem)
        return new_subsystem

    @staticmethod
    def hook_get_new_subsystem(new_subsystem):
        """Method to allow subclasses to add commands during init."""
        pass


def subsystem_init(self, parent, idx=None):
    self._parent = weakref.ref(parent)
    self.subsystem_idx = idx


def subsystem_repr(self):
    repr = self.subsystem_type
    try:
        repr += f' {self.subsystem_idx}'
    except AttributeError:
        pass
    return repr


def subsystem_get_device(self):
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
