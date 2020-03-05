from collections import namedtuple

from patchbay import ureg

ScpiTypeConverter = namedtuple('ScpiTypeConverter', 'query, write')


def parse_errors(err_str):
    err_num, err_msg = err_str.split(',', 1)
    return int(err_num), err_msg.strip('"')


def scpi_error(arg=None):
    return ScpiTypeConverter(parse_errors, None)


def scpi_bool(arg=None):
    return ScpiTypeConverter(lambda v: (bool(int(v))), int)


def scpi_qty(unit_str):
    # for now, keeping % as regular floats, but could enforce as dimensionless.
    # seems like that would be an unnecessary pain
    if unit_str == '%':
        converter = ScpiTypeConverter(lambda v: float(v) / 100,
                                      lambda v: v * 100)
    else:
        converter = ScpiTypeConverter(lambda v: float(v) * ureg(unit_str),
                                      lambda v: v.to(ureg(unit_str)).magnitude)
    return converter


def scpi_choice(choices):
    inv_choices = {v: k for k, v in choices.items()}
    return ScpiTypeConverter(lambda v: inv_choices[v], lambda v: choices[v])


# converters for strings, binary (curve)?
# converters done: boolean, quantity (including %), choices, errors


class ScpiFactory:
    def __init__(self, name):
        self.scpi_class = None
        self.reset(name)

    def reset(self, name):
        self.scpi_class = type(name, (object,), {})

    def build_from_json(self, json):
        meta, cmd_list = json
        self.reset(meta['name'])
        for cmd in cmd_list:
            name, scpi_base_cmd, scpi_type, scpi_type_arg, kwargs = cmd
            scpi_type = globals()[f'scpi_{scpi_type}'](scpi_type_arg)
            self.add_cmd(name, scpi_base_cmd, scpi_type, **kwargs)
        return self.scpi_class()

    def add_cmd(self, name, scpi_base_cmd, converter, *,
                can_query=True, can_write=True,
                query_keywords=None, write_keywords=None):
        if query_keywords is None:
            query_keywords = []
        if write_keywords is None:
            write_keywords = []

        prop_get, prop_set = None, None
        if can_query:
            cmd = self._build_command(scpi_base_cmd)
            prop_get = self._query_func(cmd, converter.query)
        if can_write:
            cmd = self._build_command(scpi_base_cmd, is_query=False)
            prop_set = self._write_func(cmd, converter.write)

        setattr(self.scpi_class, name, property(prop_get, prop_set))

        for keyword in query_keywords:
            cmd = self._build_command(scpi_base_cmd, keyword)
            setattr(self.scpi_class, f'{name}_{keyword}',
                    property(self._query_func(cmd, converter.query)))

        for keyword in write_keywords:
            cmd = self._build_command(scpi_base_cmd, keyword, is_query=False)
            setattr(self.scpi_class, f'{name}_to_{keyword}',
                    self._write_func(cmd, converter.write))

    @staticmethod
    def _build_command(base_cmd, post=None, *, is_query=True):
        q = '?' if is_query else ''
        command = base_cmd + q

        if post:
            command += ' ' + post
        elif not is_query:
            command += ' {}'

        return command

    @staticmethod
    def _query_func(command, converter):
        def query(self):
            return converter(self._parent.device.query(command))

        return query

    @staticmethod
    def _write_func(command, converter):
        if '{}' in command:
            def write(self, value):
                value = converter(value)
                self._parent.device.write(command.format(value))
        else:
            def write(self):
                self._parent.device.write(command)
        return write
