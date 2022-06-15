import setuptools
import glob
import sysconfig
import os

NAME = 'casperfpga'
DESCRIPTION = 'Talk to CASPER hardware devices using katcp or dcp. See https://github.com/casper-astro/casperfpga for more.'
URL = 'https://github.com/casper-astro/casperfpga'

AUTHOR  = 'Tyrone van Balla'
EMAIL   = 'tvanballa at ska.ac.za'
VERSION = '0.2.0' # Need to adopt the __version__.py format

here = os.path.abspath(os.path.dirname(__file__))

try:
    with open(os.path.join(here, 'README.md')) as readme:
        # long_description = readme.read().split('\n')[2]
        long_description = '\n{}'.format(readme.read())
except Exception as exc:
    # Probably didn't find the file?
    long_description = DESCRIPTION


# extra_compile_args = sysconfig.get_config_var('CFLAGS').split()
extra_compile_args = ['-O2', '-Wall']
progska_extension = setuptools.Extension(
    'casperfpga.progska',
    # sources=['progska/_progska.c', 'progska/progska.c', 'progska/th.c',
    #         'progska/netc.c', 'progska/netc.h'],
    sources=['progska/_progska.c', 'progska/progska.c', 'progska/th.c',
            'progska/netc.c'],
    include_dirs=['progska'],
    language='c',
    # extra_compile_args=extra_compile_args,
    # extra_link_args=['-static'],
)

data_files = ['tengbe_mmap.txt', 'tengbe_mmap_legacy.txt', 'fortygbe_mmap_legacy.txt']

setuptools.setup(
    name=NAME,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    download_url='https://pypi.org/project/casperfpga',
    license='GNU GPLv2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    # Specify version in-line here
    install_requires=[
        'numpy',
        'katcp>=0.7',
        'odict',
        'setuptools',
        'tornado',
        'redis',
        'tftpy==0.8.0',
    ],
    packages=['casperfpga', 'casperfpga.debug', 'casperfpga.progska'],
    package_dir={'casperfpga': 'src', 'casperfpga.debug': 'debug', 'casperfpga.progska': 'progska'},
    package_data={'casperfpga': data_files},
    scripts=glob.glob('scripts/*'),
    setup_requires=['katversion'],
    use_katversion=True,
    ext_modules=[progska_extension],
    # Required for PyPI
    keywords='casper ska meerkat fpga',
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
	    'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Astronomy',
    ]
)

# end
