SimPy compatibility API Reference
=================================

.. container:: left-col

    The :py:mod:`usim.py` package recreates the API of the :py:mod:`simpy` package.
    It serves as a drop-in replacement for SimPy in order to gradually integrate
    and migrate simulations to μSim. For use in an existing SimPy simulation,
    it is sufficient to import :py:mod:`usim.py` in place of :py:mod:`simpy`.

.. code-block:: python3

    # load the compatibility layer in place of simpy
    import usim.py as simpy

.. content-tabs:: left-col

    The :py:mod:`usim.py` package itself provides direct access to the most relevant objects.
    However, they can be fetched from their respective submodules as well.

Environments (:py:mod:`usim.py.core`)
-------------------------------------

.. content-tabs:: left-col

    =========================================================== ======================================
    :py:class:`~usim.py.core.Environment`\ ``(initial_time=0)`` Execution environment for a simulation
    ``RealtimeEnvironment(...)``                                Not supported by μSim
    =========================================================== ======================================

.. container:: content-tabs right-col

    .. hint::

        μSim simulations are started by :py:func:`usim.run`.

Events (:py:mod:`usim.py.events`)
---------------------------------

.. content-tabs:: left-col

    ============================================================= ===================================================================
    :py:class:`~usim.py.events.Event`\ (env)                      Event that is manually triggered,
    :py:class:`~usim.py.events.Timeout`\ (env, delay, value=None) Event that triggers after a ``delay``
    :py:class:`~usim.py.events.Process`\ (env, generator)         Active event that processes an event-yielding generator
    :py:class:`~usim.py.events.AllOf`\ (env, events)              Event that triggers once all ``events`` succeed
    :py:class:`~usim.py.events.AnyOf`\ (env, events)              Event that triggers once any ``events`` succeed
    :py:exc:`~usim.py.exceptions.Interrupt`\ (cause)              Exception to :py:meth:`~usim.py.events.Process.interrupt` a Process
    ============================================================= ===================================================================

.. content-tabs:: right-col

    .. hint::

        μSim simulations can ``await`` events and may
        :py:meth:`~usim.py.events.Event.succeed` and :py:meth:`~usim.py.events.Event.fail`
        them.

Resources (:py:mod:`usim.py.resources`)
---------------------------------------

.. content-tabs:: left-col

    ============================================================================= ============================================================================================
    :py:exc:`~usim.py.resources.resource.Resource`\ (env, capacity=1)             Resource with a fixed capacity of usage slots
    :py:exc:`~usim.py.resources.resource.PriorityResource`\ (env, capacity=1)     Resource with a fixed capacity of usage slots granted with priorities
    :py:exc:`~usim.py.resources.resource.PreemptiveResource`\ (env, capacity=1)   Resource with a fixed capacity of usage slots preempted with priorities
    :py:exc:`~usim.py.resources.container.Container`\ (env, capacity=inf, init=0) Resource with a fixed capacity of continuous, indistinguishable content
    :py:exc:`~usim.py.resources.store.Store`\ (env, capacity=inf)                 Resource with a fixed capacity of slots for storing arbitrary objects
    :py:exc:`~usim.py.resources.store.PriorityStore`\ (env, capacity=inf)         Resource with capacity slots for storing objects in priority order.
    :py:exc:`~usim.py.resources.store.PriorityItem`\ (priority, item)             Wrap an arbitrary item with an orderable priority.
    :py:exc:`~usim.py.resources.store.FilterStore`\ (env, capacity=inf)           Resource with capacity slots for storing arbitrary objects supporting filtered get requests.
    ============================================================================= ============================================================================================

Exceptions (:py:mod:`usim.py.exceptions`)
-----------------------------------------

.. content-tabs:: left-col

    ================================================== ===================================================================
    :py:exc:`~usim.py.exceptions.SimPyException`\ ()   Base case for all non-internal exceptions
    :py:exc:`~usim.py.exceptions.Interrupt`\ (cause)   Exception to :py:meth:`~usim.py.events.Process.interrupt` a Process
    :py:exc:`~usim.py.exceptions.StopProcess`\ (value) Exception to :py:meth:`~usim.py.core.Environment.exit` a Process
    ================================================== ===================================================================

Detailed Topics
---------------

.. content-tabs:: left-col

    .. toctree::
        :maxdepth: 2

        usim.py.resources
