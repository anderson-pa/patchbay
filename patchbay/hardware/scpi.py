from patchbay.hardware.subsystem import (ValueConverter, SubsystemFactory,
                                         HardwareNode,
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


def get_scpi_base(self):
    if self.subsystem_idx:
        return f'{self._scpi_base}{self.subsystem_idx}'
    else:
        return self._scpi_base


class ScpiNode(HardwareNode):
    def __init__(self, device):
        super().__init__(device)

        idn = device.query('*idn?')

        # find and set the termination characters if they appear in response
        for term_chrs in ['\r\n', '\r', '\n']:
            if term_chrs in idn[-2:]:
                device.read_termination = term_chrs
                idn = idn.rstrip(term_chrs)
                break

        idn = [s.strip() for s in idn.split(',')]
        self.make = self._get_make(idn[0])
        self.model = self._get_model(idn[1])
        self.serial = self._get_serial(idn[2])
        self.versions = self._get_versions(idn[3])

    def _get_make(self, idn_part):
        return idn_part

    def _get_model(self, idn_part):
        return idn_part

    def _get_serial(self, idn_part):
        return idn_part

    def _get_versions(self, idn_part):
        return idn_part


class ScpiFactory(SubsystemFactory):
    converters = {'error': scpi_error}
    choice_maps = scpi_choice_maps

    @classmethod
    def add_subsystem(cls, target, name, commands,
                      description=None, num_channels=None, zero_indexed=False,
                      **kwargs):
        subsystem = super().add_subsystem(target, name, commands, description,
                                          num_channels, zero_indexed)
        scpi_base = ':'.join([getattr(target, 'scpi_base', ''),
                              kwargs.get('scpi_base', name)])
        subsystem._scpi_base = scpi_base.lstrip(':')
        return subsystem

    @staticmethod
    def hook_get_new_subsystem(new_subsystem):
        setattr(new_subsystem, 'scpi_base', property(get_scpi_base, None))

    @staticmethod
    def query_func(command, converter, keyword=None):
        try:
            cmd = _build_command(command, keyword)
            return _query_func(cmd, converter)
        except KeyError:
            return not_implemented_func

    @staticmethod
    def write_func(command, converter, keyword=None):
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

    return f'{base_cmd}{q}{post}'.strip()


def _query_func(command, converter):
    """Get a query function that calls the given SCPI command with conversion.

    :param command: string SCPI command to query
    :param converter: converter to use for translation
    :return: SCPI query function
    """
    def query_abs_func(self):
        return converter(
            self.device.query(command.format(idx=self.subsystem_idx))
        )

    def query_func(self):
        return converter(
            self.device.query(':'.join([self.scpi_base, command]))
        )

    return query_abs_func if command.startswith(':') else query_func


def _write_func(command, converter):
    """Get a write function that calls the given SCPI command with conversion.

    :param command: string SCPI command to write
    :param converter: converter to use for translation
    :return: SCPI write function
    """

    if '{' in command and converter:
        if command.startswith(':'):
            # absolute command with value input
            def write_func(self, value):
                self.device.write(command.format(value=converter(value),
                                                 idx=self.subsystem_idx))
        else:
            # relative command with value input
            def write_func(self, value):
                value = converter(value)
                self.device.write(':'.join([self.scpi_base,
                                            command.format(value=value)]))
    else:
        if command.startswith(':'):
            # absolute command, no value input
            def write_func(self):
                self.device.write(command.format(idx=self.subsystem_idx))
        else:
            # relative command, no value input
            def write_func(self):
                self.device.write(':'.join([self.scpi_base, command]))

    return write_func


def not_implemented_func(self, *args):
    raise NotImplementedError


def recursive_get(dictionary, keys):
    for key in keys:
        dictionary = dictionary[key]
    return dictionary
