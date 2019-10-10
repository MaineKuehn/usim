μSim API Reference
==================

.. py:module:: usim
    :synopsis: The μSim namespace

The :py:mod:`usim` package provides access to the entire μSim API in one
convenient, flat namespace.
Logically, the API can be divided into different topics, however.
In addition, :py:mod:`usim.typing` allows for type annotations to statically
verify simulations.

.. hint::

    μSim provides a :ref:`compatibility layer <simpy_compatibility>`
    to the `SimPy`_ simulation framework.
    The :py:mod:`usim.py` package is a drop-in replacement
    for the :py:mod:`simpy` package.

Starting a Simulation
---------------------

Simulations in μSim always defined based on a number of initial root
:term:`activities <activity>`,
which may branch out to more :term:`activities <activity>`.
A simulation is started by calling :py:func:`usim.run`, passing in its
:term:`activities <activity>` and optionally the time window to simulate.

.. autofunction:: usim.run

Simulating Time
---------------

μSim provides a number of primitives to check or wait for specific points in time
of a simulation.

:py:data:`usim.time`
    Expressions define points in time or delays.
    For example, ``await (time + 20)`` delays for 20 time units.

:py:data:`usim.eternity`
    A point in time indefinitely far into the future

:py:data:`usim.instant`
    A point in time from the current moment.

In addition, recurring actions can be repeated at specific delays or intervals
in ``async for`` block.

:py:data:`usim.interval`
    Repeat in fixed intervals, regardless of any time spent in a block.

:py:data:`usim.delay`
    Repeat after fixed delays, in addition to any time spent in a block.

Detailed Topics
---------------

.. toctree::
    :maxdepth: 2

    usim_timing
    usim.typing

.. _SimPy: https://simpy.readthedocs.io/