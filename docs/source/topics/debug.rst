Usage Assertions and Performance
================================

.. container:: left-col

    In order to help writing correct simulations,
    μSim uses a wide range of usage assertions.
    These generally verify argument values and types in advance,
    so that you can pinpoint where errors originate.

.. container:: left-col

    At the same time, μSim strives to provide
    best performance for correct simulations.
    Once you have verified your simulation,
    you can omit all consistency assertions with zero cost.

.. container:: content-tabs right-col

    .. note:: μSim runs in assertion mode by default.

Assertions and Debug Extensions
-------------------------------

.. content-tabs:: left-col

    μSim uses assertions when checking
    the internal logic of simulations.
    For example, :term:`time` in a simulation must always advance
    into the future -
    assertions protect against creating events in the past.

.. content-tabs:: right-col

    .. code:: python3

        >>> from usim import time, run
        >>>
        >>> async def wait(delay):
        ...     await (time + delay)
        ...
        >>> run(wait(-20))  # delay until a time that has already passed

.. content-tabs:: left-col

    When run regularly, this will fail with an :py:exc:`AssertionError`.
    The error includes some information to tell you what went wrong,
    and attempts to explain how to fix it.

    In addition to validating your simulation,
    assertion mode also provides rich exception messages.
    For example, erroneously using ``await time`` provides
    an Exception with additional help on intended usage.

.. content-tabs:: right-col

    .. rubric:: Rich error messages in assertion mode

    .. code:: none

        TypeError: 'time' cannot be used in 'await' expression

        Use 'time' to derive operands for specific expressions:
        * 'await (time + duration)' to delay for a specific duration
        * 'await (time == date)' to proceed at a specific point in time
        * 'await (time >= date)' to proceed at or after a point in time
        * 'await (time < date)' to indefinitely block after a point in time

        To get the current time, use 'time.now'

Reacting to Usage Errors
------------------------

.. content-tabs:: left-col

    The purpose of assertions is to help simulation developers
    detect and remove inconsistencies and logic errors.
    They are not meant for the simulation itself to
    react to or even attempt recovery.

    When an assertion of μSim fails, this means your simulation
    is in an undefined state.
    Instead of trying to recover, you should fix the root cause
    of the erroneous condition.

.. content-tabs:: right-col

    .. code:: python3

        >>> try:
        ...     risk.take_chance()
        ... except KeyError:  # correct - recover from exception state
        ...     risk.recover()
        ... except AssertionError:  # incorrect - recover from corruption
        ...     risk.recover()

Omitting Assertions
-------------------

.. content-tabs:: left-col

    While assertions are important for verification,
    they incur a runtime performance overhead.
    If you trust your simulation to not need assertions,
    you can switch off all assertions to gain performance.

.. content-tabs:: left-col

    Starting Python with the :option:`-O` flag disables
    μSim's assertion mode.

.. content-tabs:: right-col

    .. rubric:: Simulating in optimised mode

    .. code:: bash

        python3 -O my_simulation.py

.. content-tabs:: left-col

    In optimised mode, assertions are completely removed from μSim.
    There is no runtime overhead from checking debug mode versus optimised mode.

.. content-tabs:: left-col

    In addition to disabling assertions, rich exception messages are removed as well.
    For example, erroneously using ``await time`` provides
    the regular Python error message.

.. content-tabs:: right-col

    .. rubric:: Regular Python error messages in optimized mode

    .. code:: none

        TypeError: object Time can't be used in 'await' expression

.. content-tabs:: left-col

    Notably, optimised mode throws the same exceptions as assertion mode
    (except for :py:exc:`AssertionError`).
    Only the error message differs.
