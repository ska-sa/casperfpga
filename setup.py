import setuptools
from distutils.core import setup, Extension
import glob
import sysconfig

with open("README.md", "r") as readme:
    # long_description = readme.read().split('\n')[2]
    long_description = readme.read()

# extra_compile_args = sysconfig.get_config_var('CFLAGS').split()
extra_compile_args = ['-O2', '-Wall']
progska_extension = Extension(
    'casperfpga.progska',
    ['progska/_progska.c', 'progska/progska.c', 'progska/th.c',
     'progska/netc.c'],
    include_dirs=['progska'],
    # extra_compile_args=extra_compile_args,
    # extra_link_args=['-static'],
)

setuptools.setup(
    name='casperfpga',
    version="0.1.9",
    description='Talk to CASPER hardware devices using katcp or dcp.',
    author='P. Prozesky',
    author_email='paulp@ska.ac.za',
    url="https://github.com/ska-sa/casperfpga",
    download_url="https://test.pypi.org/projects/casperfpga",
    license='LICENSE.txt',
    long_description=long_description,
    install_requires=[
        'katcp',
        'numpy',
        'odict',
    ],
    packages=['casperfpga', 'casperfpga.progska'],  # , 'casperfpga.test'],
    package_dir={'casperfpga': 'src', 'casperfpga.progska': 'progska'},
    # packages = setuptools.find_packages(),
    #packages=['casperfpga'],
    #package_dir={'casperfpga':'src'},
    scripts=glob.glob('scripts/*'),
    setup_requires=['katversion'],
    use_katversion=False,
    ext_modules=[progska_extension],
    keywords="CASPER SKA MeerKAT FPGA",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
	"Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Astronomy",
    ]
)

# end
