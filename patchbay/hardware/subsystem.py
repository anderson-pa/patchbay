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
        return cls.add_cmds(prototype, target=None)

    @classmethod
    def add_cmds(cls, prototype, target):
        """Build a subsystem on target from the prototype definition.

        Prototype is a dictionary with the keys: name, description, iterable,
        commands, subsystems.

        Each command definition is an iterable with elements: name,
        converter_type, converter_arg, kwargs

        todo: full writeup of the format once this has been refined.

        :param prototype: definition of the subsystem commands
        :param target: class to add commands to. If None, make a new class
        :return: subsystem class
        """

        if target is None:
            target = cls.get_new_subsystem(prototype['name'],
                                           prototype['description'])
        if not hasattr(target, 'keys'):
            target.keys = {}

        for cmd in prototype['commands']:
            cmd_name, cmd_type, cmd_arg, kwargs = cmd
            lookup_name = f'{prototype["name"]}.{cmd_name}'

            for kw in ['query_keywords', 'write_keywords']:
                if kw in kwargs:
                    kwargs[kw] = [key.strip() for key in kwargs[kw].split(',')]

            if cmd_type == 'choice':
                choice_map = cls.choice_map[lookup_name]
                choice_list = [arg.strip() for arg in cmd_arg.split(',')]
                cmd_arg = {key: val for key, val in choice_map.items()
                           if key in choice_list}

            cls.add_cmd(target, lookup_name, cmd_type, cmd_arg, **kwargs)

        return target

    @classmethod
    def add_cmd(cls, target, fullname, converter_func, converter_arg=None, *,
                can_query=True, can_write=True,
                query_keywords=None, write_keywords=None):
        """Add command parameters and methods to a class.

        Add a properties and methods associated with `name` to `target`,
        which is generally a subsystem class. These properties and methods
        use the converter functions as post-/pre- processors to translate
        values between Python and the device:

            Query -> query_converter(query_cmd())
            Write -> write_cmd(write_converter(value))

        If the command is query and write accessible, a property is added. A
        get/set method is used if only query/write is allowed. Otherwise, an
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
        :param converter_func: ValueConverter specific for device and argument
        :param converter_arg: argument passed to converter constructor, if any
        :param can_query: if True, a query property is added
        :param can_write: if True, a write property is added
        :param query_keywords: additional query keywords for this command
        :param write_keywords: additional write keywords for this command
        """
        name = fullname.split('.')[-1]

        if converter_func == 'choice':
            setattr(target, f'{name}_choices',
                    staticmethod(lambda: tuple(converter_arg.keys())))

        converter = converter_func(converter_arg, can_query=can_query,
                                   can_write=can_write)

        # set the property or function
        if all(converter):
            # write a property
            prop_get = cls.query_func(fullname, converter.query)
            prop_set = cls.write_func(fullname, converter.write)
            setattr(target, name, property(prop_get, prop_set))
        else:
            if converter.query is not None:
                # only a query converter so create a get method
                setattr(target, 'get_' + name,
                        cls.query_func(fullname, converter.query))
            else:
                # if only a write converter, create a get method
                # if neither, its a plain command with no inputs
                w_prefix = 'set_' if converter.write is not None else ''
                setattr(target, w_prefix + name,
                        cls.write_func(fullname, converter.write))

        # set additional properties for the keywords
        if query_keywords is None:
            query_keywords = []
        for key in query_keywords:
            setattr(target, f'{name}_{key}',
                    property(cls.query_func(fullname, converter.query, key)))

        if write_keywords is None:
            write_keywords = []
        for key in write_keywords:
            setattr(target, f'{name}_to_{key}',
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

        new_subsystem = type(name.capitalize(), (object,), {})
        new_subsystem.__init__ = __init__
        new_subsystem.__doc__ = description
        new_subsystem._device = _device
        return new_subsystem


def __init__(self, parent):
    self._parent = weakref.ref(parent)
    self.keys = {}


def _device(self):
    return self._parent().device
