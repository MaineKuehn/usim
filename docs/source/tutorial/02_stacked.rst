Raise the Stacks
================

.. container:: left-col

    As simulations grow, it is good practice to separate them into distinct parts.
    The primary means is to construct complex activities from other, simpler activities.
    When using ``usim``, there is no distinction between combining pre-made and custom activities.

    Activities can be used like notifications in other activities.
    You can ``await`` the completion of an activity just like a notification.
    This allows to stack activities, and combine them to create complex constructs.

Interlude 01: Combining Activities
----------------------------------

.. content-tabs:: left-col

    This example is similar to our `previous lesson <tutorial define activity>`_,
    but with an additional activity.
    Each activity separately uses ``usim`` to delay for some time.
    However, we use ``await`` and ``return`` to compose them to a single action.

.. container:: content-tabs right-col

    .. code:: python3

        >>> from usim import time
        >>>
        >>> async def refill(beverage):                           #1
        ...     print('Start filling', beverage, 'at', time.now)
        ...     await (time + 5)
        ...     print('Stop filling', beverage, 'at', time.now)
        ...     return 5                                          #2
        ...
        >>> async def drink(beverage='coffee', duration=20):
        ...     refill_duration = await refill(beverage)          #3
        ...     print('Refill took', refill_duration)
        ...     print('Start drinking', beverage, 'at', time.now)
        ...     await (time + duration)
        ...     print('Stop drinking', beverage, 'at', time.now)

.. content-tabs:: left-col

    Both activities extend the same basic template as used earlier.
    Take note how our activities interact with each other:

    1. Like root activities, nested activities do not need to accept some simulation state or environment.
       You can focus on the parameters that matter for the activity at hand.

    2. Nested activities may ``return`` values. [#activityreturn]_
       This works just like regular functions returning values, and ends the activity.

    3. Activities may ``await`` other activities.
       This suspends the outer activity until the inner activity finishes.
       The result of ``await`` is the ``return`` value of the inner activity.

    The takeaway is that ``await`` and ``return`` allow you to combine activities.
    Splitting your activities into smaller parts is important to build large and complex simulations.

.. content-tabs:: right-col

    .. code:: python3

        >>> from usim import run
        >>>
        >>> run(drink('tea', duration=40))   # run the root activity
        Start filling tea at 0
        Stop filling tea at 5
        Refill took 5
        Start drinking tea at 5
        Stop drinking tea at 45

Let's do many things...
-----------------------

.. content-tabs:: left-col

    So far, we have just run a fixed number of activities.
    Head over to the :doc:`next section <./03_scopes>` to write branching activities.

    .. [#activityreturn] It is a common mistake in concurrent programming to accidentally forget about return values.
                         μSim thus considers it an error if activities ``return`` something that is never received.
