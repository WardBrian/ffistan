.. py:currentmodule:: tinystan

Python Interface
================

----

Installation
------------

From Source
___________
This assumes you have followed the :doc:`Getting Started guide <../getting-started>` to install
TinyStan's pre-requisites and downloaded a copy of the TinyStan source code.

To install the Python interface, you can either install it directly from Github with

.. code-block:: shell

    pip install "git+https://github.com/WardBrian/tinystan.git#egg=tinystan&subdirectory=clients/python"

Or, since you have already downloaded the repository, you can run

.. code-block:: shell

    pip install -e python/

from the TinyStan folder.

To use the TinyStan source you've manually downloaded instead of
one the package will download for you, you must use :func:`set_tinystan_path`
or the ``$TINYSTAN`` environment variable.


Note that the Python package depends on Python 3.9+ and NumPy, and will install
NumPy if it is not already installed.

Example Program
---------------

An example program is provided alongside the Python interface code in :file:`example.py`:

.. raw:: html

   <details>
   <summary><a>Show example.py</a></summary>


.. literalinclude:: ../../clients/python/example.py
   :language: python

.. raw:: html

   </details>

API Reference
-------------

Model object
___________________

.. autoclass:: tinystan.Model
   :members:

.. autoclass:: tinystan.HMCMetric()
   :members:
   :undoc-members:

.. autoclass:: tinystan.OptimizationAlgorithm()
   :members:
   :undoc-members:

Inference outputs
_________________

.. autoclass:: tinystan.StanOutput()
   :members:


Compilation utilities
_____________________

.. autofunction:: tinystan.compile_model
.. autofunction:: tinystan.set_tinystan_path
