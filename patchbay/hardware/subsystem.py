import json
import weakref
from collections import namedtuple
from os import path

definition_file = path.join(path.dirname(__file__),
                            'subsystem_definitions.json')
with open(definition_file, 'r') as fp:
    prototype_definitions = json.load(fp)

ValueConverter = namedtuple('ValueConverter', 'query, write')


def subsystem_factory(prototype, cmd_factory):
    """Build a subsystem from the prototype using the given command factory.

    Prototype is a dictionary with the keys: name, description, iterable,
    commands, subsystems.

    Each command definition is an iterable with elements: name,
    converter_type, converter_arg, kwargs

    todo: full writeup of the format once this has been refined.

    :param prototype: definition of the subsystem commands
    :param cmd_factory: factory for generating the functions for a device
    :return: class
    """
    base_cls = get_new_subsystem(prototype['name'], prototype['description'])

    for cmd in prototype['commands']:
        name, cmd_type, cmd_arg, kwargs = cmd
        add_cmd(base_cls, cmd_factory, name, cmd_type, cmd_arg, **kwargs)

    return base_cls


def add_cmd(base_cls, factory, name, converter_type, converter_arg=None, *,
            can_query=True, can_write=True,
            query_keywords=None, write_keywords=None):
    """Add command parameters and methods to a subsystem class.

    Add a properties and methods associated with `name` to the subsystem
    class. Values are converted as appropriate to translate from Python to
    the device:

        c.name -> query_converter(query_cmd())
        c.name = value -> write_cmd(write_converter(value))

    If converters are None, then a command without parameters is added: name()

    If keywords are included, additional properties are added for each:
    `c.name_qkeyword()` and `c.name_to_wkeyword()`

    This allows for commands that have e.g., min, max, or default values.

    The different converters allow for more customization, including boolean
    conversions, enforcing units on quantities, and setting a list of choices.

    :param base_cls: class to add on to
    :param factory: class for generating the appropriate functions
    :param name: name of the attribute or method
    :param converter_type: ValueConverter specific for device and argument
    :param converter_arg: argument passed to converter constructor, if any
    :param can_query: if True, a query property is added
    :param can_write: if True, a write property is added
    :param query_keywords: additional SCPI query keywords for this command
    :param write_keywords: additional SCPI write keywords for this command
    """
    fullname = f'{base_cls.__name__.lower()}.{name}'

    if query_keywords:
        query_keywords = [key.strip() for key in query_keywords.split(',')]
    if write_keywords:
        write_keywords = [key.strip() for key in write_keywords.split(',')]
    if converter_type == 'choice':
        choice_map = factory.choice_map[fullname]
        choice_list = [arg.strip() for arg in converter_arg.split(',')]
        converter_arg = {key: val for key, val in choice_map.items()
                         if key in choice_list}

        setattr(base_cls, f'{name}_choices',
                staticmethod(lambda: tuple(converter_arg.keys())))

    converter = factory.get_converters(converter_type, converter_arg)

    # set the property or function
    if not any(converter):
        # write a function if no converters
        if can_query and converter.query is not None:
            setattr(base_cls, 'get_' + name,
                    factory.query_func(fullname, converter.query))
        if can_write:
            w_prefix = 'set_' if converter.write is not None else ''
            setattr(base_cls, w_prefix + name,
                    factory.write_func(fullname, converter.write))
    else:
        # write a property
        prop_get, prop_set = None, None
        if can_query and converter.query is not None:
            prop_get = factory.query_func(fullname, converter.query)
        if can_write and converter.write is not None:
            prop_set = factory.write_func(fullname, converter.write)

        setattr(base_cls, name, property(prop_get, prop_set))

    # set additional properties for the keywords
    if query_keywords is None:
        query_keywords = []
    for key in query_keywords:
        setattr(base_cls, f'{name}_{key}',
                property(factory.query_func(fullname, converter.query, key)))

    if write_keywords is None:
        write_keywords = []
    for key in write_keywords:
        setattr(base_cls, f'{name}_to_{key}',
                factory.write_func(fullname, None, key))


def get_new_subsystem(name, description=None):
    """Create a new, blank class to build upon.

    :param name: name of the class
    :param description: docstring description
    :return: class
    """

    def __init__(self, parent):
        self._parent = weakref.ref(parent)
        self.keys = {}

    base_class = type(name.capitalize(), (object,), {})
    base_class.__init__ = __init__
    base_class.__doc__ = description
    return base_class
