SimPy compatibility API Reference
=================================

This package and its submodules recreate the API of the :py:mod:`simpy` package.
It serves as a drop-in replacement for SimPy in order to gradually integrate
and migrate simulations to μSim. For use in an existing SimPy simulation,
it is sufficient to import :py:mod:`usim.py` in place of :py:mod:`simpy`.

.. code:: python3

    # load the compatibility layer in place of simpy
    import usim.py as simpy

The :py:mod:`usim.py` package itself provides direct access to the most relevant objects.
However, they can be fetched from their respective submodules as well.

Environments (:py:mod:`usim.py.core`)
-------------------------------------

=========================================================== ======================================
:py:class:`~usim.py.core.Environment`\ ``(initial_time=0)`` Execution environment for a simulation
``RealtimeEnvironment(...)``                                Not supported by μSim
=========================================================== ======================================

.. hint::

    μSim simulations are started by :py:func:`usim.run`.

Events (:py:mod:`usim.py.events`)
---------------------------------

============================================================= ===================================================================
:py:class:`~usim.py.events.Event`\ (env)                      Event that is manually triggered'),
:py:class:`~usim.py.events.Timeout`\ (env, delay, value=None) Event that triggers after a ``delay``
:py:class:`~usim.py.events.Process`\ (env, generator)         Active event that processes an event-yielding generator
:py:class:`~usim.py.events.AllOf`\ (env, events)              Event that triggers once all ``events`` succeed
:py:class:`~usim.py.events.AnyOf`\ (env, events)              Event that triggers once any ``events`` succeed
:py:exc:`~usim.py.exceptions.Interrupt`\ (cause)              Exception to :py:meth:`~usim.py.events.Process.interrupt` a Process
============================================================= ===================================================================

.. hint::

    μSim simulations can ``await`` events and may
    :py:meth:`~usim.py.events.Event.succeed` and :py:meth:`~usim.py.events.Event.fail`
    them.

Resources
---------

``usim.py`` implements no resources yet.

Exceptions (:py:mod:`usim.py.exceptions`)
-----------------------------------------

================================================== ===================================================================
:py:exc:`~usim.py.exceptions.SimPyException`\ ()   Base case for all non-internal exceptions
:py:exc:`~usim.py.exceptions.Interrupt`\ (cause)   Exception to :py:meth:`~usim.py.events.Process.interrupt` a Process
:py:exc:`~usim.py.exceptions.StopProcess`\ (value) Exception to :py:meth:`~usim.py.core.Environment.exit` a Process
================================================== ===================================================================
