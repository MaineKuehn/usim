μSim API Reference
==================

.. py:module:: usim
    :synopsis: The μSim namespace

The :py:mod:`usim` package provides access to the entire μSim API in one
convenient, flat namespace.
Logically, the API can be divided into different topics.
In addition, :py:mod:`usim.typing` allows for type annotations to statically
verify simulations.

.. hint::

    μSim provides a :ref:`compatibility layer <simpy_compatibility>`
    to the `SimPy`_ simulation framework.
    The :py:mod:`usim.py` package is a drop-in replacement
    for the :py:mod:`simpy` package.

Starting a Simulation
---------------------

Simulations in μSim are always defined based on a number of initial root
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
    A point in time indefinitely far into the future.

:py:data:`usim.instant`
    A point in time indistinguishable from the current moment.

In addition, recurring actions can be repeated at specific delays or intervals
in ``async for`` blocks.

:py:data:`usim.interval`
    Repeat in fixed intervals, regardless of any time spent in a block.

:py:data:`usim.delay`
    Repeat after fixed delays, in addition to any time spent in a block.

Branching and Multitasking
--------------------------

An :term:`activity` may not only ``await`` another,
it may also run one or more :term:`activities <activity>` concurrently.
This requires opening a scope in an ``async with`` context
which defines the lifetime of child activities.

:py:class:`usim.Scope`
    An :term:`asynchronous context manager` which can concurrently
    run :term:`activities <activity>` until it is closed.
    A scope is forcefully closed if an exception occurs
    in the hosting :term:`activity` or a child.

:py:func:`usim.until`
    A :py:class:`~usim.Scope` that is forcefully closed
    if a specific notification triggers.

Each child :term:`activity` is represented by a :py:class:`~usim.typing.Task`.
Tasks can be inspected for their current status,
and various exceptions only occur when interacting with tasks.

:py:class:`usim.TaskState`
    Enum describing the possible :py:meth:`~usim.typing.Task.status`
    of a :py:class:`~usim.typing.Task`.

:py:exc:`usim.TaskClosed` and :py:exc:`usim.VolatileTaskClosed`
    The exception value of a :py:class:`~usim.typing.Task` that was forcefully
    closed by its :py:class:`~usim.Scope`.

:py:exc:`usim.CancelTask` and :py:exc:`usim.TaskCancelled`
    Exception used to :py:meth:`~usim.typing.Task.cancel`
    a :py:class:`~usim.typing.Task`,
    and the resulting exception value of the :py:class:`~usim.typing.Task`.

During a :py:class:`usim.Scope`,
multiple child activities may fail with an exception at the same time.
The :py:class:`usim.Scope` collects and propagates all exceptions from child activities.

:py:exc:`usim.Concurrent`
    Exception that propagates all exceptions from child activities at once;
    also occurs if only a single child activity fails.
    Never includes an exception raised in the scope itself.

Synchronising Conditions
------------------------

μSim allows to model any boolean that may change at a later time
as a :py:class:`~usim.typing.Condition`.
These can be combined and negated to derive new :py:class:`~usim.typing.Condition`\ s.

:py:class:`usim.Flag`
    A :py:class:`~usim.typing.Condition` with a fixed value which can be explicitly
    :py:meth:`~usim.Flag.set` to either :py:data:`True` or :py:data:`False`.

It is common for types to return a :py:class:`~usim.typing.Condition` instead of
a plain :py:class:`bool`.

:py:class:`usim.Tracked`
    A mutable value which can be explicitly :py:meth:`~usim.Tracked.set` or modified
    using arithmetic operators, such as ``+``, ``-``, ``*`` or ``/``.
    Comparison operators, such as ``==``, ``<=`` or ``>``, provide
    a :py:class:`~usim.typing.Condition` which triggers once the value matches.

Sharing State
-------------

Concurrently running :term:`activities <activity>` frequently need to access,
modify or exchange state.
μSim provides several types to easily write :term:`activities <activity>` that
safely share state.

:py:class:`usim.Lock`
    Ensure mutually exclusive access for multiple activities.

:py:class:`usim.Channel`
    Broadcast messages to multiple subscribers.

:py:class:`usim.Queue`
    Send and receive unique messages.

:py:exc:`usim.StreamClosed`
    Exception for operations not supported by a closed
    :py:class:`~usim.Channel` or :py:class:`~usim.Queue`

Modelling Resources
-------------------

Simulations commonly revolve around resources which are produced/consumed,
blocked or waited for.
μSim implements a range of generic, ready-to-use resources for various use-cases.

:py:class:`usim.Resources`
    Supply of named resources which can be temporarily borrowed
    or permanently produced/consumed.

:py:class:`usim.Capacities`
    Fixed supply of named resources which can be temporarily borrowed.

:py:class:`usim.typing.ResourceLevels`
    Current, expected or desired levels of resources.

:py:exc:`usim.ResourcesUnavailable`
    Exception raised when an attempt to :py:meth:`~usim.Resources.claim`
    resources fails.

Common Building Blocks
----------------------

:py:func:`usim.first`
    Run several :term:`activities <activity>` concurrently and yield results
    as they become available.

:py:func:`usim.collect`
    Run several :term:`activities <activity>` concurrently and return
    their results in order.

Detailed Topics
---------------

.. toctree::
    :maxdepth: 2

    usim_timing
    usim_branching
    usim_synchronising
    usim_sharing
    usim_resources
    usim_common
    usim.typing

.. _SimPy: https://simpy.readthedocs.io/
