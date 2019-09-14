"""
SimPy to μSim compatibility layer
=================================

This package and its submodules recreate the API of the ``simpy`` package.
It serves as a drop-in replacement for SimPy in order to gradually integrate
and migrate simulations to μSim. For use in an existing SimPy simulation,
it is sufficient to import ``usim.py`` in place of ``simpy``.

.. code:: python3

    # load the compatibility layer in place of simpy
    import usim.py as simpy

The ``usim.py`` package itself provides direct access to the most relevant objects.
However, they can be fetched from their respective submodules as well.
"""
from .core import Environment
from .exceptions import Interrupt
from .events import Event, Timeout, Process, AllOf, AnyOf

__all__ = ['Environment', 'Interrupt', 'Event', 'Timeout', 'Process', 'AllOf', 'AnyOf']
