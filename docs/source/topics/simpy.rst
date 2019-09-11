SimPy Compatibility
===================

    SimPy_ is a process-based discrete-event simulation framework
    based on standard Python.

    --- The SimPy Documentation

Both μSim and SimPy are discrete, event-based simulation frameworks.
While SimPy is built on generators and callbacks, μSim relies exclusively
on the ``async``/``await`` coroutine support introduced in Python 3.5.
This makes a difference both in the usage, as well as supported features.

To allow running, integrating and migrating existing SimPy simulations,
μSim has an inbuilt compatibility layer: the :py:mod:`usim.py` module
provides most of the SimPy API. The only truly unsupported feature are scheduling
priorities - due to its high concurrency, μSim is optimised for FIFO scheduling.

Using μSim in a SimPy Simulation
--------------------------------

As :py:mod:`usim.py` replicates the :py:mod:`simpy` API, it is sufficient
to change imports to ``usim.py`` instead of ``simpy``. If your simulation
uses the ``simpy`` namespace directly, you can alias ``usim.py`` to ``simpy``.
Otherwise, import objects from ``usim.py`` instead of ``usim``.

+------------------------------------+--------------------------------------+
|                                    |                                      |
| SimPy native imports               | μSim compatibility imports           |
|                                    |                                      |
| .. code:: python3                  |  .. code:: python3                   |
|                                    |                                      |
|     # module import                |     # alias to expected name         |
|     import simpy                   |     import usim.py as simpy          |
|     # object import                |     # import objects                 |
|     from simpy import Environment  |     from usim.py import Environment  |
|                                    |                                      |
+------------------------------------+--------------------------------------+

Changing imports is all that is required to switch from SimPy to the μSim
compatibility layer. The core of the `first SimPy example`_ is exactly the
same for the μSim compatibility layer:

.. code:: python3

    >>> def car(env):
    ...     while True:
    ...         print('Start parking at %d' % env.now)
    ...         parking_duration = 5
    ...         yield env.timeout(parking_duration)
    ...
    ...         print('Start driving at %d' % env.now)
    ...         trip_duration = 2
    ...         yield env.timeout(trip_duration)
    ...

Running this example is *almost* the same as for SimPy:
only the single line previously used to ``import simpy`` needs changing.

.. code:: python3

    >>> import usim.py as simpy  # import usim.py instead of simpy
    >>> env = simpy.Environment()
    >>> env.process(car(env))
    <Process(car) object at 0x...>
    >>> env.run(until=15)
    Start parking at 0
    Start driving at 5
    Start parking at 7
    Start driving at 12
    Start parking at 14

The ``usim.py`` layer not only provides the SimPy API, it can even interoperate with native
μSim simulations. This allows combining simulations from μSim and SimPy, and
to gradually convert simulations.

.. hint::

    The :py:mod:`usim.py` documentation also describes how compatibility objects
    can be used directly in native μSim activities.

Interactions between μSim and SimPy
-----------------------------------

The :py:mod:`usim.py` compatibility layer allows to use SimPy elements in μSim
and vice versa. This works by translating the fundamental elements of each framework:

* a Simpy :py:class:`~usim.py.Event` can be ``await``\ ed in a μSim activity, and
* a μSim :term:`activity` can be ``yield``\ ed by a SimPy Process.

Both approaches *return* the value or *raise* any errors of their activity or event.
This gives full access to all SimPy features from μSim --
however, there is no equivalent to μSim's ``async for`` and ``async with`` in SimPy.

.. code:: python3

    >>> from usim import time
    >>> def car(env):
    ...     """Partially migrated SimPy process"""
    ...     trip_duration = 2
    ...     parking_duration = 5
    ...     while True:
    ...         print(f'Start parking at {env.now}')
    ...         yield (time + parking_duration)
    ...
    ...         print(f'Start driving at {env.now}')
    ...         yield (time + trip_duration)
    ...

Note that a :py:class:`~usim.py.Process` may directly ``await`` any :term:`activity`
-- there is no need to wrap an :term:`activity` in another :py:class:`~usim.py.Process`.
You can use all features of μSim in an :term:`activity`,
even when it is ``yield``\ ed from a :py:class:`~usim.py.Process`.

Migrating from SimPy to μSim
----------------------------

To access the full capabilities of μSim, you should write native μSim simulations.
Due to the compatibility layer, it is possible to migrate individual pieces.
The most important difference is that μSim :term:`activities <activity>` are ``async def`` coroutines
which ``await`` events. In addition, there is no environment that must be passed around
-- all :py:mod:`usim` primitives automatically find their containing simulation.

.. code:: python3

    >>> from usim import run, time
    >>> async def car():
    ...     """Fully migrated SimPy process"""
    ...     while True:
    ...         print(f'Start parking at {time.now}')
    ...         await (time + 5)
    ...         print(f'Start driving at {time.now}')
    ...         await (time + 2)
    ...
    >>> run(car(), till=15)
    # Start parking at 0
    # Start driving at 5
    # Start parking at 7
    # Start driving at 12
    # Start parking at 14

When migrating a SimPy simulation to  μSim, keep in mind that μSim already provides
many high-level features of simulations.
For example, μSim's ``async for`` works well to express repetitive tasks:

.. code:: python3

    >>> from usim import run, time, delay
    >>> async def car():
    ...     print(f'Start parking at {time.now}')
    ...     async for _ in delay(5):
    ...         print(f'Start driving at {time.now}')
    ...         await (time + 2)
    ...         print(f'Start parking at {time.now}')

.. _SimPy: https://simpy.readthedocs.io/
.. _first SimPy example: https://simpy.readthedocs.io/en/latest/simpy_intro/basic_concepts.html
