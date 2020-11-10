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


# converters for strings (needed?), binary (e.g. curve)?
function_shapes = {'sinusoid': 'SIN',
                   'square': 'SQU',
                   'triangle': 'TRI',
                   'ramp': 'RAMP',
                   'noise': 'NOIS',
                   'custom': 'USER',
                   }

scpi_choice_maps = {'shape': function_shapes,
                    'amplitude_unit': {'Vpp': 'VPP',
                                       'Vrms': 'VRMS',
                                       'dBm': 'DBM'},
                    }

scpi_cmd_map = {
    'am':
        {'enabled': 'am:state',
         'shape': 'am:internal:function',
         'frequency': 'am:internal:frequency',
         'depth': 'am{source}:depth',
         },
    'source':
        {'enabled': 'source{source}',
         'shape': 'source{source}:function:shape',
         'frequency': 'source{source}:frequency',
         'amplitude': 'source{source}:voltage',
         'offset': 'source{source}:voltage:offset',
         'amplitude_unit': 'source{source}:voltage:unit',
         },
    'system':
        {'error': 'system:error',
         },
}


class ScpiFactory(SubsystemFactory):
    converters = {'error': scpi_error}
    choice_maps = scpi_choice_maps

    @staticmethod
    def query_func(name, converter, command, keyword=None):
        try:
            cmd = _build_command(command, keyword)
            return _query_func(cmd, converter)
        except KeyError:
            return not_implemented_func

    @staticmethod
    def write_func(name, converter, command, keyword=None):
        try:
            cmd = _build_command(command, keyword, is_query=False)
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
            self.device.query(command.format(source=self.subsystem_idx)))

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
                self.device.write(command.format(source=self.subsystem_idx))
        else:
            def write_func(self, value):
                value = converter(value)
                self.device.write(command.format(source=self.subsystem_idx,
                                                 value=value))
    else:
        def write_func(self):
            self.device.write(command)
    return write_func


def not_implemented_func(self, *args):
    raise NotImplementedError


def recursive_get(dictionary, keys):
    for key in keys:
        dictionary = dictionary[key]
    return dictionary
