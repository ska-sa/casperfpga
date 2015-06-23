from distutils.core import setup
import glob

setup(
    name='casperfpga',
    version='0.0.1',
    author='P.Prozesky',
    author_email='paulp@ska.ac.za',
    # scripts=['bin/stowe-towels.py','bin/wash-towels.py'],
    url='',
    license='LICENSE.txt',
    description='Talk to CASPER fpga devices using katcp or dcp.',
    long_description=open('README.txt').read(),
    install_requires=[
        'katcp',
        'numpy',
    ],
    provides=['casperfpga'],
    packages=['casperfpga'],  # , 'casperfpga.test'],
    package_dir={'casperfpga': 'src'},
    scripts=glob.glob('scripts/*')
)

# end
