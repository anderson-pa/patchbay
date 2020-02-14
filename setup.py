import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='patchbay',
    version='0.0.1',
    author='Phillip Anderson',
    author_email='python.patchbay@gmail.com',
    description='High level automation and device communication.',
    license='Fair Source 0.9 (10)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/anderson-pa/patchbay',
    packages=setuptools.find_packages(),
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
