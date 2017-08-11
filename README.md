# casperfpga #

`casperfpga` is a python library used to interact and interface with [**CASPER** Hardware](https://casper.berkeley.edu/wiki/Hardware). Functionality includes being able to reconfigure firmware, as well as read and write registers across the various communication interfaces.

This README will outline, and make reference to, the following:
1. Notes to Users
   1. [New Users](#new-users)
   2. [Existing Users](#existing-users)
2. [Installation](#installation)
3. [Usage](#usage)
   1. [Getting Started](https://casper.berkeley.edu/wiki/Tutorials)
   2. [Methods and Utilities](https://github.com/ska-sa/casperfpga/wiki/API-Documentation)
4. [Contributing](#contributing)


## Notes to casperfpga users ##

### New Users ###

Not much to say to new users except welcome! It goes without saying that once you have cloned this respository you should make sure you're on the correct branch (usually **master**, unless you're a contributor) and always pull regularly. This, to make sure you have the latest version of casperfpga with the latest features. You can move on straight to [Installation](#installation).

Should you be an existing `corr` user, wondering where some of your functionality has gone when interfacing to your ROACH/2, please [look here](https://github.com/ska-sa/casperfpga/wiki/Migrating-from-corr-to-casperfpga) for a detailed explanation on **How to migrate to `casperfpga`**.

### Existing Users ###

From commit [`a5e7dcc`](https://github.com/ska-sa/casperfpga/tree/a5e7dcc05d4b0234d05e808fc6b8ab91485b8051) and earlier the method of instantiating e.g. a SKARAB object was as follows:

```python
In [1]: import casperfpga
In [2]: skarab = casperfpga.SkarabFpga('skarab010103')
In [3]: roach = casperfpga.katcp_fpga.KatcpFpga('roach020203')
```

As of commit [`4adffc0`](https://github.com/ska-sa/casperfpga/commit/4adffc0994c56c38dafe6a395d3ed94e8e9477cc) the method of instantiating a ROACH or SKARAB was altered to be done intelligently. `casperfpga` automatically works out whether the parameter given in its instantiation is a SKARAB or ROACH board.

```python
In [1]: import casperfpga
In [2]: skarab = casperfpga.CasperFpga('skarab010103')
DEBUG:root:skarab010103 seems to be a SKARAB
INFO:casperfpga.transport_skarab:skarab010103: port(30584) created & connected.
DEBUG:root:casperfpga.casperfpga:skarab010103: now a CasperFpga
In [3]: roach = casperfpga.CasperFpga('roach020203')
DEBUG:root:roach020203 seems to be a ROACH
INFO:casperfpga.transport_katcp:roach020203: port(7147) created and connected.
DEBUG:root:casperfpga.casperfpga:roach020203: now a CasperFpga
```

## Installation ##
There are a number of prerequisites required for the casperfpga package.

```shell
$ sudo apt-get install python-pip
$ sudo pip install ply tornado futures futures unittest2 mock ProxyTypes numpy
$ # mock might give some warnings, they are not critical and can be ignored.
```

Then clone the casperfpga repository. The **master** branch is home to the latest, most stable build of casperfpga.

```shell
$ git clone https://github.com/ska-sa/casperfpga.git
$ cd casperfpga
$ sudo python setup.py install
[sudo] password for user:
```

To check that casperfpga has been installed correctly open an ipython session and import casperfpga.
```shell
$ ipython
```
```python
In [1]: import casperfpga
```

If you receive any errors after this please feel free to contact anyone on the [CASPER Mailing List](mailto:casper@lists.berkeley.edu), or check the [Mailing List Archive](http://www.mail-archive.com/casper@lists.berkeley.edu/) to see if your issue has been resolved already.

## Usage ##
The introductory tutorials for [ROACH](https://casper.berkeley.edu/wiki/Introduction_to_Simulink), [ROACH2](https://casper.berkeley.edu/wiki/Introduction_to_Simulink_ROACH2) and [SKARAB](https://casper.berkeley.edu/wiki/Introduction_to_Simulink_SKARAB) serve as a guide to the entire process of:
* Creating an FPGA design in Simulink using the CASPER and Xilinx Blocksets
* Building the design using the toolflow, and lastly
* Reconfiguring your CASPER Hardware with the generated .fpg file using `casperfpga`

`casperfpga` is written in python and mainly used to communicate with CASPER Hardware and reconfigure it's firmware. Hence the medium of communication is usually done through an ipython session, as shown below:

```python
import casperfpga
fpga = casperfpga.CasperFpga('skarab_host or roach_name')
fpga.upload_to_ram_and_program('your_file.fpg')
```

## Contributing ##

Fork this repo, add your changes and issue a pull request.
