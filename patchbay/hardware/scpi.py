import builtins
from functools import lru_cache

from patchbay import ureg
from patchbay.hardware.subsystem import (ValueConverter, SubsystemFactory,
                                         add_can_querywrite_keywords)


def parse_error(err_str):
    """Split an error string into components.

    Assumed form for SCPI errors is `<int>, "description"`. This is used for
    the error converter.

    :param err_str: string from the SCPI instrument
    :return: tuple (int, string)
    """
    err_num, err_msg = err_str.split(',', 1)
    return int(err_num), err_msg.strip('"')


@add_can_querywrite_keywords
def scpi_error(_=None):
    """Get a SCPI converter for errors.

    Errors are a one-way communication, so the write converter is not needed.
    `arg` is present only to keep the signature consistent with other
    converters.

    :param _: placeholder for signature matching to other converter functions
    :return: ValueConverter for errors
    """
    return ValueConverter(parse_error, None)


@add_can_querywrite_keywords
def scpi_bool(_=None):
    """Get a SCPI converter for booleans.

    Booleans are written to the device as 0/1 typically, so convert to int.
    Queries typically return 0/1 as a string, so convert to int and then
    boolean.

    :param _: placeholder for signature matching to other converter functions
    :return: ValueConverter for booleans
    """
    return ValueConverter(lambda v: (bool(int(v))), int)


@add_can_querywrite_keywords
def scpi_num(dtype):
    """Get a SCPI converter for unit-less numbers.

    :param dtype: name of type to convert to (e.g. 'int', 'float')
    :return: ValueConverter for nums
    """
    return ValueConverter(getattr(builtins, dtype), lambda v: v)


@lru_cache()  # don't create multiple functions for the same conversion
def qty_query_converter(unit_str):
    """Get a SCPI query converter function for quantities.

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
    """Get a SCPI write converter function for quantities.

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
            raise ValueError(f'Value has no units.')
        return base_unit_value.magnitude

    write_converter.__doc__ = str(write_converter.__doc__).format(unit=unit_str)
    return write_converter


def value_to_percent(v):
    return v * 100


def value_from_percent(v):
    return float(v)/100


@add_can_querywrite_keywords
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
    :return: ValueConverter for quantities
    """
    if unit_str == '%':
        converter = ValueConverter(value_from_percent, value_to_percent)
    else:
        converter = ValueConverter(qty_query_converter(unit_str),
                                   qty_write_converter(unit_str))
    return converter


@add_can_querywrite_keywords
def scpi_choice(choices):
    """Get a SCPI converter for choice lists.

    Some SCPI commands allow a restricted set of choices (essentially an
    enum). Use a list if the keywords for the instrument and the Python
    interface should be the same. Otherwise pass a dictionary with Python
    names for the keys and instrument names for the values.

    :param choices: list or dict of choice options
    :return: ValueConverter for a list of choices
    """
    try:
        inv_choices = {v: k for k, v in choices.items()}
    except AttributeError:
        inv_choices = choices

    return ValueConverter(lambda v: inv_choices[v], lambda v: choices[v])


# converters for strings (needed?), binary (e.g. curve)?
function_shapes = {'sinusoid': 'SIN',
                   'square': 'SQU',
                   'triangle': 'TRI',
                   'ramp': 'RAMP',
                   'noise': 'NOIS',
                   'custom': 'USER',
                   }

scpi_converter_map = {'error': scpi_error,
                      'bool': scpi_bool,
                      'qty': scpi_qty,
                      'choice': scpi_choice
                      }

scpi_choice_map = {'amplitude_modulation.shape': function_shapes,
                   'source.shape': function_shapes,
                   'source.amplitude_unit': {'Vpp': 'VPP',
                                             'Vrms': 'VRMS',
                                             'dBm': 'DBM'},
                   }

scpi_cmd_map = {'amplitude_modulation.enabled': 'am:state',
                'amplitude_modulation.shape': 'am:internal:function',
                'amplitude_modulation.frequency': 'am:internal:frequency',
                'amplitude_modulation.depth': 'am{source}:depth',
                'source.enabled': 'source{source}',
                'source.shape': 'source{source}:function:shape',
                'source.frequency': 'source{source}:frequency',
                'source.amplitude': 'source{source}:voltage',
                'source.offset': 'source{source}:voltage:offset',
                'source.amplitude_unit': 'source{source}:voltage:unit',
                'system.error': 'system:error',
                }


class ScpiFactory(SubsystemFactory):

    choice_map = scpi_choice_map
    converter_map = scpi_converter_map

    def __init__(self, prototype_name):
        self.prototype_name = prototype_name

    def __call__(self, prototype_name, *args, **kwargs):
        self.prototype_name = prototype_name

    @staticmethod
    def query_func(name, converter, keyword=None):
        try:
            cmd = _build_command(scpi_cmd_map[name], keyword)
            return _query_func(cmd, converter)
        except KeyError:
            return not_implemented_func

    @staticmethod
    def write_func(name, converter, keyword=None):
        try:
            cmd = _build_command(scpi_cmd_map[name], keyword, is_query=False)
            return _write_func(cmd, converter)
        except KeyError:
            return not_implemented_func


def _build_command(base_cmd, post=None, *, is_query=True):
    """Build a SCPI command from the base string.

    :param base_cmd: the root SCPI command
    :param post: keyword that comes after the command, or None
    :param is_query: if True, format the command as a query
    :return: string command
    """
    q = '?' if is_query else ''
    if post is not None:
        post = ' ' + post
    elif not is_query:
        post = ' {value}'
    else:
        post = ''

    return f'{base_cmd}{q}{post}'


def _query_func(command, converter):
    """Get a query function that calls the given SCPI command with conversion.

    :param command: string SCPI command to query
    :param converter: converter to use for translation
    :return: SCPI query function
    """

    def query_func(self):
        return converter(
            self._device().query(command.format(**self.keys)))

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
                self._device().write(command.format(**self.keys))
        else:
            def write_func(self, value):
                value = converter(value)
                self._device().write(command.format(**self.keys, value=value))
    else:
        def write_func(self):
            self._device().write(command)
    return write_func


def not_implemented_func(self, *args):
    raise NotImplementedError
