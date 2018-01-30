import setuptools
from distutils.core import setup, Extension
import glob
import sysconfig

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
    author='P.Prozesky',
    author_email='paulp@ska.ac.za',
    url='http://pypi.python.org/pypi/casperfpga',
    license='LICENSE.txt',
    description='Talk to CASPER fpga devices using katcp or dcp.',
    long_description=open('README.txt').read(),
    install_requires=[
        'katcp',
        'numpy',
        'odict',
    ],
    # provides=['casperfpga'],
    packages=['casperfpga', 'casperfpga.progska'],  # , 'casperfpga.test'],
    package_dir={'casperfpga': 'src', 'casperfpga.progska': 'progska'},
    # package_data={'': ['LMX2581*.txt']},
    # package_data={'casperfpga.progska': ['progska/progska.so']},
    # include_package_data=True,
    scripts=glob.glob('scripts/*'),
    setup_requires=['katversion'],
    use_katversion=True,
    ext_modules=[progska_extension],
)

# end
