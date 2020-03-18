import json
import weakref
from collections import namedtuple
from functools import wraps
from os import path

_defs_file = path.join(path.dirname(__file__), 'subsystem_definitions.json')
with open(_defs_file, 'r') as fp:
    prototype_definitions = json.load(fp)

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
    converter_map = {}
    choice_map = {}

    @classmethod
    def new_subsystem(cls, prototype):
        return cls.add_cmds(prototype, base_cls=None)

    @classmethod
    def add_cmds(cls, prototype, base_cls):
        """Build a subsystem from the prototype using the given command factory.

        Prototype is a dictionary with the keys: name, description, iterable,
        commands, subsystems.

        Each command definition is an iterable with elements: name,
        converter_type, converter_arg, kwargs

        todo: full writeup of the format once this has been refined.

        :param prototype: definition of the subsystem commands
        :param base_cls: class to add commands to. If None, make a new class
        :return: subsystem class
        """

        if base_cls is None:
            base_cls = cls.get_new_subsystem(prototype['name'],
                                             prototype['description'])
        if not hasattr(base_cls, 'keys'):
            base_cls.keys = {}

        for cmd in prototype['commands']:
            cmd_name, cmd_type, cmd_arg, kwargs = cmd

            cls.add_cmd(base_cls, f'{prototype["name"]}.{cmd_name}',
                        cmd_type, cmd_arg, **kwargs)

        return base_cls

    @classmethod
    def add_cmd(cls, base_cls, name, converter_type, converter_arg=None, *,
                can_query=True, can_write=True,
                query_keywords=None, write_keywords=None):
        """Add command parameters and methods to a subsystem class.

        Add a properties and methods associated with `name` to the subsystem
        class. Values are converted as appropriate to translate from Python to
        the device:

            c.name -> query_converter(query_cmd())
            c.name = value -> write_cmd(write_converter(value))

        If converters are None, then a command without parameters is added:
        name()

        If keywords are included, additional properties are added for each:
        `c.name_qkeyword()` and `c.name_to_wkeyword()`

        This allows for commands that have e.g., min, max, or default values.

        The different converters allow for more customization, including
        boolean conversions, enforcing units on quantities, and setting a
        list of choices.

        :param base_cls: class to add on to
        :param name: name of the attribute or method
        :param converter_type: ValueConverter specific for device and argument
        :param converter_arg: argument passed to converter constructor, if any
        :param can_query: if True, a query property is added
        :param can_write: if True, a write property is added
        :param query_keywords: additional query keywords for this command
        :param write_keywords: additional write keywords for this command
        """
        fullname = name
        name = fullname.split('.')[-1]

        if query_keywords:
            query_keywords = [key.strip() for key in query_keywords.split(',')]
        if write_keywords:
            write_keywords = [key.strip() for key in write_keywords.split(',')]
        if converter_type == 'choice':
            choice_map = cls.choice_map[fullname]
            choice_list = [arg.strip() for arg in converter_arg.split(',')]
            converter_arg = {key: val for key, val in choice_map.items()
                             if key in choice_list}

            setattr(base_cls, f'{name}_choices',
                    staticmethod(lambda: tuple(converter_arg.keys())))

        converter = cls.converter_map[converter_type](converter_arg,
                                                      can_query=can_query,
                                                      can_write=can_write)

        # set the property or function
        if not all(converter):
            # write a function if no converters
            if converter.query is not None:
                setattr(base_cls, 'get_' + name,
                        cls.query_func(fullname, converter.query))
            else:
                w_prefix = 'set_' if converter.write is not None else ''
                setattr(base_cls, w_prefix + name,
                        cls.write_func(fullname, converter.write))
        else:
            # write a property
            prop_get, prop_set = None, None
            if converter.query is not None:
                prop_get = cls.query_func(fullname, converter.query)
            if converter.write is not None:
                prop_set = cls.write_func(fullname, converter.write)

            setattr(base_cls, name, property(prop_get, prop_set))

        # set additional properties for the keywords
        if query_keywords is None:
            query_keywords = []
        for key in query_keywords:
            setattr(base_cls, f'{name}_{key}',
                    property(cls.query_func(fullname, converter.query, key)))

        if write_keywords is None:
            write_keywords = []
        for key in write_keywords:
            setattr(base_cls, f'{name}_to_{key}',
                    cls.write_func(fullname, None, key))

    @staticmethod
    def query_func(name, converter, keyword=None):
        raise NotImplementedError

    @staticmethod
    def write_func(name, converter, keyword=None):
        raise NotImplementedError

    @staticmethod
    def get_new_subsystem(name, description=None):
        """Create a new, blank class to build upon.

        :param name: name of the class
        :param description: docstring description
        :return: class
        """

        base_class = type(name.capitalize(), (object,), {})
        base_class.__init__ = __init__
        base_class.__doc__ = description
        base_class._device = _device
        return base_class


def __init__(self, parent):
    self._parent = weakref.ref(parent)
    self.keys = {}


def _device(self):
    return self._parent().device
