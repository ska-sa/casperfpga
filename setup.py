import setuptools
from distutils.core import Extension #, setup
import glob
# import sysconfig

with open("README.md", "r") as readme:
    long_description = readme.read().split('\n')[2]

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
    version='0.0.1',
    author='P.Prozesky',
    author_email='paulp@ska.ac.za',
    url='https://github.com/casper-astro/casperfpga',
    license='LICENSE.txt',
    description='Talk to CASPER fpga devices using katcp or dcp.',
    long_description=open('README.txt').read(),
    install_requires=[
        'katcp',
        'numpy',
        'odict',
    ],
    provides=['casperfpga'],
    packages=['casperfpga'],  # , 'casperfpga.test'],
    package_dir={'casperfpga': 'src'},
    package_data={'' : ['LMX2581*.txt']},
    include_package_data=True,
    scripts=glob.glob('scripts/*'),
    setup_requires=['katversion'],
    use_katversion=True,
    ext_modules=[progska_extension],
    # How do I tell it to point to some 'unpackable version' of Jack's TFTPY
    # dependency_links=['https://github.com/casper-astro/'],
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Operating System :: Limited by MATLAB and Xilinx Support",
    ]
)

# end
