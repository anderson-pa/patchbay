import builtins
import json
import weakref
from collections import namedtuple
from functools import lru_cache

from patchbay import ureg

ScpiTypeConverter = namedtuple('ScpiTypeConverter', 'query, write')


def parse_errors(err_str):
    """Split an error string into components.

    Assumed form for SCPI errors is `<int>, "description"`. This is used for
    the error converter.

    :param err_str: string from the SCPI instrument
    :return: tuple (int, string)
    """
    err_num, err_msg = err_str.split(',', 1)
    return int(err_num), err_msg.strip('"')


def scpi_error(arg=None):
    """Get a SCPI converter for errors.

    Errors are a one-way communication, so the write converter is not needed.
    `arg` is present only to keep the signature consistent with other
    converters.

    :param arg: not used. only present for signature consistency.
    :return: ScpiTypeConverter for errors
    """
    return ScpiTypeConverter(parse_errors, None)


def scpi_bool(arg=None):
    """Get a SCPI converter for booleans.

    Booleans are written to the device as 0/1 typically, so convert to int.
    Queries typically return 0/1 as a string, so convert to int and then
    boolean.

    :param arg: not used. only present for signature consistency
    :return: ScpiTypeConverter for booleans
    """
    return ScpiTypeConverter(lambda v: (bool(int(v))), int)


def scpi_num(dtype):
    """Get a SCPI converter for unit-less numbers.

    :param dtype: name of type to convert to (e.g. 'int', 'float')
    :return: ScpiTypeConverter for nums
    """
    return ScpiTypeConverter(getattr(builtins, dtype),
                             lambda v: v)


@lru_cache()  # don't create multiple functions for the same conversion
def qty_write_converter(unit_str):
    """Get a converter function for scpi_qty.

    Return a function that converts an input value to the given base unit.
    The returned function will raises a ValueError if the value is not a pint
    quantity.

    :param unit_str: string representation of the unit for this converter
    :return: function for qty write conversions.
    """

    def write_converter(value):
        try:
            base_unit_value = value.to(ureg(unit_str))
        except AttributeError:
            raise ValueError(f'Value has no units.')
        return base_unit_value.magnitude

    return write_converter


def scpi_qty(unit_str):
    """Get a SCPI converter for quantities.

    Generate a converter to send and recieve unit-aware quantities to a
    device. Values sent to the device only need to have the right
    dimensionality so that pint can convert to the unit that the device
    expects.

    This uses the base unit without SI prefixes to avoid possible order or
    magnitude errors. Since SCPI is case-insensitive, `milli` and `Mega` (for
    example) are ambiguous and one is usually assumed.

    Percentages could be converted to dimensionless pint quantities but for
    now just treated as regular floats. Not clear that the extra overhead is
    useful.

    :param unit_str: string representation of the unit for this command
    :return: ScpiTypeConverter for quantities
    """
    if unit_str == '%':
        converter = ScpiTypeConverter(lambda v: float(v) / 100,
                                      lambda v: v * 100)
    else:
        converter = ScpiTypeConverter(lambda v: float(v) * ureg(unit_str),
                                      qty_write_converter(unit_str))
    return converter


def scpi_choice(choices):
    """Get a SCPI converter for choice lists.

    Some SCPI commands allow a restricted set of choices (essentially an
    enum). Use a list if the keywords for the instrument and the Python
    interface should be the same. Otherwise pass a dictionary with Python
    names for the keys and instrument names for the values.

    :param choices: list or dict of choice options
    :return: ScpiTypeConverter for a list of choices
    """
    try:
        inv_choices = {v: k for k, v in choices.items()}
    except AttributeError:
        inv_choices = choices

    return ScpiTypeConverter(lambda v: inv_choices[v], lambda v: choices[v])


# converters for strings (needed?), binary (e.g. curve)?


def scpi_subsystems_from_specs(channel_specs):
    sub_systems = {}
    for channel_id, json_file in channel_specs.items():
        with open(json_file, 'r') as fp:
            js = json.load(fp)
        if isinstance(channel_id, tuple):
            scpi_sub = scpi_subsystem_from_json(js, channel_id[0])
        else:
            scpi_sub = scpi_subsystem_from_json(js)
        sub_systems[channel_id] = scpi_sub
    return sub_systems


def scpi_subsystem_from_json(json_str, *args):
    """Build or add on to a SCPI Subsystem class from a json description.

    :param json_str: json string describing the SCPI subsystem
    :param base_cls: class to add commands to. If `None`, a new class is made.
    :param args: used as formatters for `scpi_base_cmd`s
    :return: updated class object
    """
    meta = json_str[0]
    base_cls = get_blank_scpi_subsystem(meta['name'], meta['description'])

    for cmd in meta['commands']:
        name, scpi_base_cmd, scpi_type, scpi_type_arg, scpi_kwargs = cmd
        scpi_base_cmd = scpi_base_cmd.format(*args)
        scpi_type = globals()[f'scpi_{scpi_type}'](scpi_type_arg)
        add_scpi_cmd(base_cls, name, scpi_base_cmd, scpi_type, **scpi_kwargs)

    return base_cls


def partial_format(st, *args):
    """Might use this to partially format base cmds"""
    try:
        return st.format(*args)
    except IndexError:
        return st
    except KeyError:
        for arg in args:
            st = st.replace(f'{{}}', str(arg), 1)
        return st


def add_scpi_cmd(base_cls, name, scpi_base_cmd, converter, *,
                 can_query=True, can_write=True,
                 query_keywords=None, write_keywords=None):
    """Add parameters to a class for SCPI commands.

    Add a property named `name` to the class that calls the corresponding
    SCPI command. Values are converted as appropriate to translate from
    Python to the device:

        c.name -> query_converter(query('scpi_base_cmd?'))
        c.name = value -> write('scpi_base_cmd write(converter(value)')

    If keywords are included, additional properties are added:
        c.name_qkeyword -> query_converter(query('scpi_base_cmd? qkeyword'))
        c.name_to_wkeyword -> write('scpi_base_cmd wkeyword')

    This allows for commands that have e.g., min, max, or default values.

    The different converters allow for more customization, including boolean
    conversions, enforcing units on quantities, and setting a list of choices.

    :param base_cls: class to add on to
    :param name: name of the attribute or method
    :param scpi_base_cmd: string for the SCPI command
    :param converter: ScpiTypeConverter to translate between python and device
    :param can_query: if True, a query property is added
    :param can_write: if True, a write property is added
    :param query_keywords: additional SCPI query keywords for this command
    :param write_keywords: additional SCPI write keywords for this command
    """
    if converter is None:
        converter = ScpiTypeConverter(None, None)

    # set the property or function
    if '{' in scpi_base_cmd or not any(converter):
        # write a function if unfilled {} in base_cmd or no converters
        if can_query and converter.query is not None:
            setattr(base_cls, 'get_' + name,
                    _query_func(scpi_base_cmd, converter.query))
        if can_write:
            w_prefix = 'set_' if converter.write is not None else ''
            setattr(base_cls, w_prefix + name,
                    _write_func(scpi_base_cmd, converter.write))
    else:
        # write a property
        prop_get, prop_set = None, None
        if can_query and converter.query is not None:
            cmd = _build_command(scpi_base_cmd)
            prop_get = _query_func(cmd, converter.query)
        if can_write and converter.write is not None:
            cmd = _build_command(scpi_base_cmd, is_query=False)
            prop_set = _write_func(cmd, converter.write)

        setattr(base_cls, name, property(prop_get, prop_set))

    # set additional properties for the keywords
    if query_keywords is None:
        query_keywords = []
    for keyword in query_keywords:
        cmd = _build_command(scpi_base_cmd, keyword)
        setattr(base_cls, f'{name}_{keyword}',
                property(_query_func(cmd, converter.query)))

    if write_keywords is None:
        write_keywords = []
    for keyword in write_keywords:
        cmd = _build_command(scpi_base_cmd, keyword, is_query=False)
        setattr(base_cls, f'{name}_to_{keyword}', _write_func(cmd, None))


def get_blank_scpi_subsystem(cls_name, cls_description=None):
    """Create a new, blank class to build upon.

    :param cls_name: name of the class
    :param cls_description: docstring description
    :return: class
    """

    def __init__(self, parent):
        self._parent = weakref.ref(parent)
        self.keys = {}

    base_cls = type(cls_name, (object,), {})
    base_cls.__init__ = __init__
    base_cls.__doc__ = cls_description
    return base_cls


def _build_command(base_cmd, post=None, *, is_query=True):
    """Build a SCPI command.

    :param base_cmd: the root SCPI command
    :param post: keyword that comes after the command, or None
    :param is_query: if True, format the command as a query
    :return: string command
    """
    q = '?' if is_query else ''
    command = base_cmd + q

    if post:
        command += ' ' + post
    elif not is_query:
        command += ' {value}'

    return command


def _query_func(command, converter):
    """Get a query function that calls the given SCPI command with conversion.

    :param command: string SCPI command to query
    :param converter: converter to use for translation
    :return: SCPI query function
    """

    if '{' in command:
        def query_func(self, *args):
            return converter(self._parent().device.query(command.format(*args)))
    else:
        def query_func(self):
            return converter(self._parent().device.query(command))

    return query_func


def _write_func(command, converter):
    """Get a write function that calls the given SCPI command with conversion.

    :param command: string SCPI command to write
    :param converter: converter to use for translation
    :return: SCPI write function
    """
    if '{' in command:
        if converter is None:
            def write_func(self):
                self._parent().device.write(command.format(**self.keys))
        else:
            def write_func(self, value):
                value = converter(value)
                self._parent().device.write(command.format(**self.keys,
                                                           value=value))
    else:
        def write_func(self):
            self._parent().device.write(command)
    return write_func
