**********
casperfpga
**********

Welcome to the documentation for ``casperfpga``, the Python-based communications package for `CASPER Hardware <https://casper.berkeley.edu/wiki/Hardware>`__!

What is casperfpga?
###################

``casperfpga`` is a Python library used to interact and interface with `CASPER Hardware <https://casper.berkeley.edu/wiki/Hardware>`__. Functionality includes being able to reconfigure firmware, as well as read and write registers across the various communication interfaces. The info here describes the following:

#. :ref:`installation_reference_label`
#. :ref:`usage_reference_label`
#. :ref:`contributing_reference_label`

Should you want to dive straight into its usage with `the toolflow proper <https://casper-toolflow.readthedocs.io/en/latest/>`__, `please see here <https://casper.berkeley.edu/wiki/Tutorials>`__.

.. _installation_reference_label:

Installation
#############

`casperfpga <https://pypi.org/project/casperfpga/>`__ is now available on the Python Package Index (PyPI) and can be installed via `pip <https://pip.pypa.io/en/stable/>`__. However, should you need to interface with a SNAP board, your installation workflow involves the extra step of installing against ``casperfpga's requirements.txt``.

.. code-block:: bash

    $ git clone https://github.com/casper-astro/casperfpga
    $ cd casperfpga/
    $ sudo apt-get install python-pip
    $ sudo pip install -r requirements.txt
    $ sudo pip install casperfpga

The distribution on the Python Package Index is, of course, a built-distribution; this contains an already-compiled version of the SKARAB programming utility ``progska``, written in ``C``. Operating Systems tested using ``pip install casperfpga`` include:

#. Ubuntu 14.04, 16.04 LTS
#. Debian 8.x

Unfortunately the success of your installation using ``pip`` depends on the host OS of the installation, and you might need to rebuild the utility using the C-compiler native to your OS. In short, follow the more traditional method of installing custom Python packages.

.. code-block:: bash

    $ git clone https://github.com/casper-astro/casperfpga.git
    $ cd casperfpga
    $ sudo pip install -r requirements.txt
    $ sudo python setup.py install

To check that casperfpga has been installed correctly open an ipython session and import casperfpga.

.. code-block:: bash

    $ ipython

.. code-block:: python

    In [1]: import casperfpga
    *

If you receive any errors after this please feel free to contact anyone on the `CASPER Mailing List <mailto:casper@lists.berkeley.edu>`_, or check the `Mailing List Archive <http://www.mail-archive.com/casper@lists.berkeley.edu/>`__ to see if your issue has been resolved already.

.. _usage_reference_label:

Usage
#####
The introductory tutorials for `ROACH <https://casper.berkeley.edu/wiki/Introduction_to_Simulink>`__, `ROACH2 <https://casper.berkeley.edu/wiki/Introduction_to_Simulink_ROACH2>`__ and `SKARAB <https://casper.berkeley.edu/wiki/Introduction_to_Simulink_SKARAB>`__ serve as a guide to the entire process of:

* Creating an FPGA design in Simulink using the CASPER and Xilinx Blocksets
* Building the design using the toolflow, and lastly
* Reconfiguring your CASPER Hardware with the generated .fpg file using `casperfpga`

``casperfpga`` is written in Python and mainly used to communicate with CASPER Hardware and reconfigure its firmware. Hence the medium of communication is usually done through an ``ipython`` session, as shown below:

.. code-block:: python

    import casperfpga
    fpga = casperfpga.CasperFpga('skarab_host or roach_name')
    fpga.upload_to_ram_and_program('your_file.fpg')

.. _contributing_reference_label:

Contributing
############

Fork `this <https://github.com/casper-astro/casperfpga>`__ repo, add your changes and issue a pull request.


.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Documentation

    migrating_from_corr
    casperfpga