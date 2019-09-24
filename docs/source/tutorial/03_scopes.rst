Branch Out
==========

.. container:: left-col

    Many simulations need additional, concurrent activities in addition to their initial activities.
    However, concurrent programming is error-prone when actions are separated from each other.
    To handle this safely, μSim requires existing activities to branch out only temporarily.

    Activities may branch out only after defining a scope of concurrency.
    The most basic scope is opened by entering an ``async with Scope()`` context.
    In turn, a scope may ``do`` several activities at once while it is active.

.. _tutorial basic scope:

Lesson 02: Using a Concurrent Scope
-----------------------------------

.. content-tabs:: left-col

    In this example, we define an activity that uses a ``Scope`` to concurrently run another activity several times.
    Scopes are opened using ````async with Scope() as <name>:``,
    followed by a block of actions which it covers. [#blockscope]_
    We again use ``usim.time`` to track and influence the progression of our simulation.

.. container:: content-tabs right-col

    .. code:: python3

        >>> from usim import time, Scope
        >>>
        >>> async def deliver_one(which):
        ...     print('Delivering', which, 'at', time.now)
        ...     await (time + 5)
        ...     print('Delivered', which, 'at', time.now)
        ...
        >>> async def deliver_all():
        ...     print('-- Start deliveries at', time.now)
        ...     async with Scope() as drivers:             # 1
        ...         drivers.do(deliver_one(1))             # 2
        ...         drivers.do(deliver_one(2))
        ...         await (time + 1)                       # 3
        ...         drivers.do(deliver_one(3))
        ...         print('Sent deliveries at', time.now)  # 4.1
        ...     print('-- Done deliveries at', time.now)   # 4.2

.. content-tabs:: left-col

    Scopes can be difficult because they are inherently about doing several things at once.
    It helps to step through individual points of notice:

    1. A scope must always be opened as an ``async with`` context - this allows us to suspend and resume
       branched off activities.
       You can freely choose a name; we recommend a name that reflects your simulation story.

    2. Activities are branched off using ``scope.do(activity)`` in place of ``await activity``.
       The current activity does *not* wait for the branched off activity to start or finish at this point.

    3. The current activity is free to perform other actions inside a scope.
       This includes calling functions and ``await``\ ing notifications,
       or using loops/functions to create more activities to do.

    4. Transitioning out of a scope is delayed until all branched off activities have finished. [#volatile]_
       Statements directly before and after the end of scope do not happen in the same :term:`turn`.

    The primary purpose of scopes is to keep concurrent activities comprehensible.

.. content-tabs:: right-col

    .. code:: python3

        >>> from usim import run
        >>>
        >>> run(deliver_all())
        -- Start deliveries at 0
        Delivering 1 at 0
        Delivering 2 at 0
        Sent deliveries at 1
        Delivering 3 at 1
        Delivered 1 at 5
        Delivered 2 at 5
        Delivered 3 at 6
        -- Done deliveries at 6

Let's take a step back...
-------------------------

.. content-tabs:: left-col

    So far, we have just run all activities to completion.
    Head over to the :doc:`next section <./04_cancel_scope>` to cancel activities and notifications.

    .. [#blockscope] Notably, the block of the scope may contain other blocks and call out to functions.
                     The scope applies to all of them, and can be passed down to functions if needed.

    .. [#volatile] The exception are ``volatile`` activities.
