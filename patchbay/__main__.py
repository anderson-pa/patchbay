import sys

import click

from patchbay import launch_gui, __version__


def main_gui():
    sys.exit(launch_gui())


@click.command()
@click.argument('filename', required=False,
                type=click.Path(exists=True, dir_okay=False))
def main(filename):
    """Launch a patch file

    \f
    :param filename:
    :return:
    """
    print(f'patchbay v{__version__}')

    return launch_gui(filename)


if __name__ == '__main__':
    main()
