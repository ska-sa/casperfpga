from setuptools import setup
#from distutils.core import setup
import glob

setup(
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
    provides=['casperfpga'],
    packages=['casperfpga'],  # , 'casperfpga.test'],
    package_dir={'casperfpga': 'src'},
    package_data={'' : ['LMX2581*.txt']},
    include_package_data=True,
    scripts=glob.glob('scripts/*'),
    setup_requires=['katversion'],
    use_katversion=True
)

# end
