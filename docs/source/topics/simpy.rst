SimPy Compatibility
===================

    SimPy_ is a process-based discrete-event simulation framework
    based on standard Python.

Both μSim and SimPy are discrete, event-based simulation frameworks.
Whereas SimPy is built on generators and callbacks, μSim relies exclusively
on the ``async``/``await`` coroutine support introduced in Python 3.5.
This makes a difference both in the usage, as well as supported features.

To allow running, integrating and migrating existing SimPy simulations,
μSim has an inbuilt compatibility layer: the :py:mod:`usim.py` module
emulates most of the SimPy API. The only truly unsupported feature are scheduling
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
compatibility layer. The following runs the first SimPy example by changing
only the single line previously used to ``import simpy``.

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

The ``usim.py`` layer not only emulates SimPy - it can also be used from native
μSim simulations. This allows to combine simulations from μSim and SimPy, and
to gradually convert simulations.

.. hint::

    The :py:mod:`usim.py` documentation also describes how compatibility objects
    can be used directly in native μSim activities.

Migrating from SimPy to μSim
----------------------------

To access the full capabilities of μSim, one should write native μSim simulations.
Due to the compatibility layer, it is possible to migrate individual pieces.
The most import difference is that μSim activities are ``async def`` coroutines
which ``await`` events. In addition, there is not environment that must be passed
around; various helpers work automatically.

.. code:: python3

    from usim import run, time

    async def car():
        while True:
            print(f'Start parking at {time.now}')
            await (time + 5)
            print(f'Start driving at {time.now}')
            await (time + 2)

    run(car(), till=15)
    # Start parking at 0
    # Start driving at 5
    # Start parking at 7
    # Start driving at 12
    # Start parking at 14

.. _SimPy: https://simpy.readthedocs.io/
