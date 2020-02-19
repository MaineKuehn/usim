Branching Tasks and Concurrent Exceptions
=========================================

Branching off from an :term:`activity` is only possible in
a well-defined :py:class:`~usim.Scope`. Each scope is bound to the lifetime
of any child :py:class:`~usim.typing.Task` to prevent stray concurrency.
Exceptions occurring concurrently are collected by the scope
into a single :py:exc:`~usim.Concurrent` exception.

Scoping Concurrency
-------------------

.. autoclass:: usim.Scope
    :members:

.. autofunction:: usim.until
    :async-with:

Managing Task Lifetime
----------------------

.. autoclass:: usim.typing.Task(...)
    :members:

.. autoclass:: usim.TaskState
    :members:

.. autoexception:: usim.TaskClosed
    :members:

.. autoexception:: usim.VolatileTaskClosed
    :members:

.. autoexception:: usim.CancelTask
    :members:

.. autoexception:: usim.TaskCancelled
    :members:

Handling Concurrent Failure
---------------------------

.. autoexception:: usim.Concurrent
    :members:

.. seealso::


    For the use of :py:exc:`AssertionError` by μSim, see also :doc:`./debug`.