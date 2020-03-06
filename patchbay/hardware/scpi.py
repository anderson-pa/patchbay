import builtins
from collections import namedtuple

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
    def qty_to_scpi(unit_str):
        def write_converter(value):
            try:
                base_unit_value = value.to(ureg(unit_str))
            except AttributeError:
                raise ValueError(f'Value has no units.')
            return base_unit_value.magnitude
        return write_converter

    if unit_str == '%':
        converter = ScpiTypeConverter(lambda v: float(v) / 100,
                                      lambda v: v * 100)
    else:
        converter = ScpiTypeConverter(lambda v: float(v) * ureg(unit_str),
                                      qty_to_scpi(unit_str))
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


def scpi_subsystem_from_json(json, base_cls=None, *args):
    meta, cmd_list = json

    if base_cls is None:
        base_cls = get_blank_scpi_subsystem(meta['name'], meta['description'])

    for cmd in cmd_list:
        name, scpi_base_cmd, scpi_type, scpi_type_arg, scpi_kwargs = cmd
        scpi_base_cmd = scpi_base_cmd.format(*args)
        scpi_type = globals()[f'scpi_{scpi_type}'](scpi_type_arg)
        add_scpi_cmd(base_cls, name, scpi_base_cmd, scpi_type, **scpi_kwargs)
    return base_cls


def add_scpi_cmd(base_cls, name, scpi_base_cmd, converter, *,
                 can_query=True, can_write=True,
                 query_keywords=None, write_keywords=None):
    if query_keywords is None:
        query_keywords = []
    if write_keywords is None:
        write_keywords = []

    prop_get, prop_set = None, None
    if can_query:
        cmd = _build_command(scpi_base_cmd)
        prop_get = _query_func(cmd, converter.query)
    if can_write:
        cmd = _build_command(scpi_base_cmd, is_query=False)
        prop_set = _write_func(cmd, converter.write)

    setattr(base_cls, name, property(prop_get, prop_set))

    for keyword in query_keywords:
        cmd = _build_command(scpi_base_cmd, keyword)
        setattr(base_cls, f'{name}_{keyword}',
                property(_query_func(cmd, converter.query)))

    for keyword in write_keywords:
        cmd = _build_command(scpi_base_cmd, keyword, is_query=False)
        setattr(base_cls, f'{name}_to_{keyword}',
                _write_func(cmd, converter.write))


def get_blank_scpi_subsystem(cls_name, cls_description=None):
    base_cls = type(cls_name, (object,), {})
    base_cls.__doc__ = cls_description
    return base_cls


def _build_command(base_cmd, post=None, *, is_query=True):
    q = '?' if is_query else ''
    command = base_cmd + q

    if post:
        command += ' ' + post
    elif not is_query:
        command += ' {}'

    return command


def _query_func(command, converter):
    def query(self):
        return converter(self._parent.device.query(command))

    return query


def _write_func(command, converter):
    if '{}' in command:
        def write(self, value):
            value = converter(value)
            self._parent.device.write(command.format(value))
    else:
        def write(self):
            self._parent.device.write(command)
    return write
