
Getting Started
===============

Requirement: C++ toolchain
--------------------------

Stan requires a C++ tool chain consisting of

* A C++14 compiler. On Windows, MSCV is *not* supported, so something like MinGW GCC is required.
* The Gnu :command:`make` utility.

Here are complete instructions by platform for installing both, from the CmdStan installation instructions.

* `C++ tool chain installation - CmdStan User's Guide <https://mc-stan.org/docs/cmdstan-guide/installation.html#cpp-toolchain>`__

Downloading TinyStan
----------------------

.. note::
    The :doc:`Julia <languages/julia>`, :doc:`Python <languages/python>`, and :doc:`R <languages/r>`
    clients will download the source for you the first time you compile a model.
    This section is *optional* for users primarily interested in those interfaces.


Installing TinyStan is as simple as ensuring that the above requirements are installed and then downloading
the source repository. All of the following ways of downloading TinyStan will additionally download the
`Stan <https://github.com/stan-dev/stan>`__ and `Stan Math <https://github.com/stan-dev/math>`__ libraries for you,
and no additional dependencies are required to be installed separately for the C++ source code.


Downloading a released archive
______________________________

Downloads of a complete copy of the source code and interfaces are available
on `our GitHub releases page <https://github.com/WardBrian/tinystan/releases>`__.

To use these, simply download the file associated with the version you wish to use,
and unzip its contents into the folder you would like TinyStan to be in.


Installing the latest version with :command:`git`
_________________________________________________

If you have :command:`git` installed, you may download TinyStan by navigating to the folder you'd like
TinyStan to be in and running

.. code-block:: shell

    git clone --recurse-submodules --shallow-submodules --depth=1 https://github.com/WardBrian/tinystan.git

If you clone without the ``--recurse-submodules`` argument, you can download the required
submodules with ``make stan-update``. The arguments ``--shallow-submodules`` and ``--depth=1`` are
to reduce the size of the download, but are not required.


Testing the Installation
________________________

After this, TinyStan is installed. You can test a basic compilation by opening
a terminal in your TinyStan folder and running

.. code-block:: shell

    # MacOS and Linux
    make test_models/multi/multi_model.so

This will compile the file :file:`test_models/multi/multi.stan` into a shared library object for use with TinyStan.
This will require internet access the first time you run it in order
to download the appropriate Stan compiler for your platform into
:file:`{<tinystan-dir>}/bin/stanc{[.exe]}`

Installing an Interface
-----------------------

To see instructions for installing the TinyStan client package in your language of
choice, see the :doc:`Language Interfaces page <languages>`.

Optional: Customizing TinyStan
--------------------------------

TinyStan has many compiler flags and options set by default. Many of these defaults
are the same as those used by the CmdStan interface to Stan.
You can override the defaults or add new flags
on the command line when invoking :command:`make`, or make them persistent by
creating or editing the file :file:`{<tinystan dir>}/make/local`.

For example, setting the contents of :file:`make/local` to the following
includes compiler flags for optimization level and architecture.

.. code-block:: Makefile

    # By default we use -O3, this sets a less aggressive C++ optimization level
    O=2
    # Adding other arbitrary C++ compiler flags
    CXXFLAGS+= -march=native

Flags for :command:`stanc3` can also be set here

.. code-block:: Makefile

    # pedantic mode and level 1 optimization
    STANCFLAGS+= --warn-pedantic --O1


Using External C++ Code
_______________________

TinyStan supports the same `capability to plug in external C++ code as CmdStan <https://mc-stan.org/docs/cmdstan-guide/external_code.html>`_.

Namely, you can declare a function in your Stan model and then define it in a separate C++ file.
This requires passing the ``--allow-undefined`` flag to the Stan compiler when building your model.
The :makevar:`USER_HEADER` variable must point to the C++ file containing the function definition.
By default, this will be the file :file:`user_header.hpp` in the same directory as the Stan model.

For a more complete example, consult the `CmdStan documentation <https://mc-stan.org/docs/cmdstan-guide/external_code.html>`_.

Using Pre-Existing Stan Installations
_____________________________________

If you wish to use TinyStan with a pre-existing download of the Stan repository, or with
a custom fork or branch, you can set the :makevar:`STAN` (and, optionally, :makevar:`MATH`) variables to the
path to your existing copy in calls to :command:`make`, or more permanently by setting them in a
:file:`make/local` file as described above.

The easiest way to use a custom stanc3 is to place the built executable at
:file:`bin/stanc{[.exe]}`.
