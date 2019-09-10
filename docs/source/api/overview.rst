μSim API Reference
==================

The :py:mod:`usim` package provides access to the entire μSim API in one
convenient, flat namespace.
Logically, the API can be divided into different topics, however.
In addition, :py:mod:`usim.typing` allows for type annotations to statically
verify simulations.

Starting a Simulation
---------------------

.. autofunction:: usim.run

Simulating Time
---------------

μSim provides a number of primitives to control time in a simulation.

======================== ======================================================
:py:data:`usim.time`     used to define or delay until arbitrary points in time
:py:data:`usim.eternity` a delay time indefinitely in the future
:py:data:`usim.instant`  a delay time indistinguishable from the current time
:py:data:`usim.interval` a repeated delay by a fixed interval
:py:data:`usim.delay`    a repeated delay
======================== ======================================================

Detailed Topics
---------------

.. toctree::
    :maxdepth: 2

    timing
