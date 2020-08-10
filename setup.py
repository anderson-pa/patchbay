import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

with open('patchbay/__init__.py', 'r') as fh:
    for line in fh:
        if line.startswith('__version__'):
            pb_version = line.split("'")[1]
            break
    else:
        raise RuntimeError("Unable to find version string.")

setuptools.setup(
    name='patchbay',
    version=pb_version,
    author='Phillip Anderson',
    author_email='python.patchbay@gmail.com',
    description='High level automation and device communication.',
    entry_points={'console_scripts':
                      ['patchbay = patchbay.__main__:main'],
                  'gui_scripts':
                      ['patchbay-ui = patchbay.__main__:main_gui']
                  },
    install_requires=['click', 'matplotlib', 'numpy', 'pandas', 'pint'],
    license='Fair Source 0.9 [10]',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/anderson-pa/patchbay',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Development Status :: 1 - Planning'
    ],
    python_requires='>=3.6',
)
