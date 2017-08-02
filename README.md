# casperfpga #

`casperfpga` is a python library used to interact and interface with [**CASPER** Hardware](https://casper.berkeley.edu/wiki/Hardware). Functionality includes being able to reconfigure firmware, as well as read and write registers across the various communication interfaces.

This README will outline, and make reference to, the following:
1. Installation
2. Usage
   1. [Getting Started](https://casper.berkeley.edu/wiki/Tutorials)
3. Contributing

### NOTE to existing casperfpga users: ###

From commit [`a5e7dcc`](https://github.com/ska-sa/casperfpga/tree/a5e7dcc05d4b0234d05e808fc6b8ab91485b8051) and earlier the method of instantiating e.g. a SKARAB object was as follows:

> `In [1]: import casperfpga`

> `In [2]: skarab = casperfpga.SkarabFpga('skarab010103')`

> `In [3]: roach = casperfpga.katcp_fpga.KatcpFpga('roach020203')`

As of commit [`4adffc0`](https://github.com/ska-sa/casperfpga/commit/4adffc0994c56c38dafe6a395d3ed94e8e9477cc) the method of isntantiating a ROACH or SKARAB was altered to be done intelligently. `casperfpga` automatically works out whether the parameter given in its instantiation is a SKARAB or ROACH board.

> `In [1]: import casperfpga`

> `In [2]: skarab = casperfpga.CasperFpga('skarab010103')`

> `DEBUG:root:skarab010103 seems to be a SKARAB`

> `**`

> `INFO:casperfpga.transport_skarab:skarab010103: port(30584) created & connected.`

> `DEBUG:root:casperfpga.casperfpga:skarab010103: now a CasperFpga`

> `**`

> `In [3]: roach = casperfpga.CasperFpga('roach020203')`

> `DEBUG:root:roach020203 seems to be a ROACH`

> `**`

> `INFO:casperfpga.transport_katcp:roach020203: port(7147) created and connected.`

> `DEBUG:root:casperfpga.casperfpga:roach020203: now a CasperFpga`


## 1. Installation ##
First, you will need to clone the casperfpga repository. The **master** branch is home to the latest, most stable build of casperfpga.

It is most common to have SKARABs/ROACHs connected to a server, allowing multiple users to gain access remotely.

```
user@this-pc:~/home/user$ ssh user@some-server
user@some-server's password:
*
user@some-server:~/home/user$ git clone https://github.com/ska-sa/casperfpga.git
user@some-server:~/home/user$ cd casperfpga
user@some-server:~/home/user/casperfpga$ sudo python setup.py install
[sudo] password for user:
*
*
```
Given the user has admin privileges on the server, executing the steps above will install casperfpga for all users on this server.

## 2. Usage ##
[This tutorial](https://casper.berkeley.edu/wiki/Introduction_to_Simulink_SKARAB) serves as a guide to the entire process of:
* Creating an FPGA design in Simulink using the CASPER and Xilinx Blocksets
* Building the design using the toolflow, and lastly
* Reconfiguring your SKARAB board with the generated .fpg file

`casperfpga` is written in python and mainly used to communicate with CASPER Hardware and reconfigure it's firmware. Hence the medium of communication is usually done through an ipython session, as shown below:

```
user@this-pc:~/home/user$ ipython

import casperfpga
fpga = casperfpga.CasperFpga('skarab_host or roach_name')
fpga.upload_to_ram_and_program('your_file.fpg')
```

## 3. Contributing ##

Nothing figured out just yet!

## Release notes-ish ##

* [2015-05-19 Tue] Requires rootfs 8dff433-2015-05-18 (or newer?) for the
  updated ?tap-multicast-remove request