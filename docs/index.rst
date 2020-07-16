**********
casperfpga
**********

Welcome to the documentation for ``casperfpga``, the Python-based communications package for `CASPER Hardware <https://casper.berkeley.edu/wiki/Hardware>`__!

New Users
#########

``casperfpga`` is a Python library used to interact and interface with `CASPER Hardware <https://casper.berkeley.edu/wiki/Hardware>`__. Functionality includes being able to reconfigure firmware, as well as read and write registers across the various communication interfaces. The info here describes the following:

1. :doc:`Installing casperfpga <How-to-install-casperfpga>`
2. :doc:`Migrating from corr <migrating_from_corr>`
3. :doc:`casperfpga Sourcecode <casperfpga>`

Should you be an existing `corr` user, wondering where some of your functionality has gone when interfacing to your ROACH/2, `'Migtrating from corr' <https://github.com/casper-astro/casperfpga/wiki/Migrating-from-corr-to-casperfpga>`__ above offers a detailed explanation on how to migrate to ``casperfpga``. 

Should you want to dive straight into its usage with `the toolflow proper <https://casper-toolflow.readthedocs.io/en/latest/>`__, `please see here <https://casper-tutorials.readthedocs.io/en/latest/>`__.

Existing Users
##############

From commit `a5e7dcc <https://github.com/ska-sa/casperfpga/tree/a5e7dcc05d4b0234d05e808fc6b8ab91485b8051>`__ and earlier the method of instantiating e.g. a SKARAB object was as follows:

.. code-block:: python

   In [1]: import casperfpga
   In [2]: skarab = casperfpga.SkarabFpga('skarab010103')
   In [3]: roach = casperfpga.katcp_fpga.KatcpFpga('roach020203')

As of commit `4adffc0 <https://github.com/ska-sa/casperfpga/commit/4adffc0994c56c38dafe6a395d3ed94e8e9477cc>`__ the method of instantiating a ROACH or SKARAB was altered to be done intelligently. ``casperfpga`` automatically works out whether the hostname given in its instantiation is a ROACH, SKARAB or SNAP board.

.. code-block:: python

   In [1]: import casperfpga
   In [2]: skarab = casperfpga.CasperFpga('skarab010103')
   DEBUG:root:skarab010103 seems to be a SKARAB
   INFO:casperfpga.transport_skarab:skarab010103: port(30584) created & connected.
   DEBUG:root:casperfpga.casperfpga:skarab010103: now a CasperFpga
   In [3]: roach = casperfpga.CasperFpga('roach020203')
   DEBUG:root:roach020203 seems to be a ROACH
   INFO:casperfpga.transport_katcp:roach020203: port(7147) created and connected.
   DEBUG:root:casperfpga.casperfpga:roach020203: now a CasperFpga

Contributing 
############
If you would like to contribute towards this library, fork the casperfpga `repo <https://github.com/casper-astro/casperfpga>`__, add your changes to the fork and issue a pull request to the parent repo.

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: casperfpga Documentation

    How-to-install-casperfpga
    migrating_from_corr
    casperfpga

..  toctree::
    :hidden:
    :maxdepth: 1
    :caption: Other Documentation

    CASPER Documentation <https://casper-toolflow.readthedocs.io/en/latest/>
    CASPER Tutorials <http://casper-tutorials.readthedocs.io/en/latest/>
