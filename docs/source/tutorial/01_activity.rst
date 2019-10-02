Getting Active
==============

.. container:: left-col

    .. toctree::

    Simulations in μSim are made from two parts:
    :term:`activities <Activity>` doing things
    and
    :term:`notifications <Notification>` orchestrating things.
    The basics of both are provided by ``usim``,
    but usually you want to build some custom activities.

    Activities are implemented as special functions, namely as :term:`coroutines <coroutine>`
    In short, this means you must use ``async def`` instead of just ``def``.
    In return, you can use the special keywords ``await`` and ``async for``/``async with``.

.. _tutorial define activity:

Lesson 01: Defining an Activity
-------------------------------

.. content-tabs:: left-col

    In this example, we define our own activity and ``await`` a pre-defined notification.
    Activities are defined using ``async def <name>(<parameters>):``,
    followed by the actions making up the activity.
    We use ``usim.time`` to track and receive notifications about the progression of time in our simulation.

.. container:: content-tabs right-col

    .. code:: python3

        >>> from usim import time
        >>>
        >>> async def drink(beverage='coffee', duration=20):       # 1
        ...     print('Start drinking', beverage, 'at', time.now)  # 2
        ...     await (time + duration)                            # 3
        ...     print('Stop drinking', beverage, 'at', time.now)

.. content-tabs:: left-col

    For the most part, activities are regular functions.
    Take a look at how our activity compares to other functions:

    1. Activities *must* be defined using ``async def`` - this allows us to suspend and resume activities.
       μSim *does not* require a specific signature, however.
       You are free to use any parameters that you see fit.

    2. You can freely call other functions, such as ``print``.
       All non-suspending features of μSim, such as ``time.now``, behave like regular objects and functions.

    3. Activities can be suspended and resumed on notification using ``await``.
       You can construct notifications regularly, such as ``time + duration`` marking a point in the future.

    The takeaway is that you use ``async``/``await`` when you need activities suspended/resumed on notifications.
    For everything else, such as querying the simulation state, you do not need to take special actions.

Epilogue 01: Running an Activity
--------------------------------

.. content-tabs:: left-col

    With our activity defined, we can now use it as our first, small simulation!
    Any activity must be instantiated by calling it;
    this allows to fill in parameters and re-use activities.
    In order to run it, we pass the instantiated activity to ``usim.run``.

.. content-tabs:: right-col

    .. code:: python3

        >>> from usim import run
        >>>
        >>> drink_coffee = drink()  # instantiate activity
        >>> run(drink_coffee)       # run the activity instance
        Start drinking coffee at 0
        Stop drinking coffee at 20

.. content-tabs:: left-col

    By calling ``usim.run``, we start the simulation at the *root activities* passed in.
    μSim can handle multiple root activities;
    they are started in :term:`turn` but at the same simulation :term:`time`.
    For example, we can use our activity several times.

.. content-tabs:: right-col

    .. code:: python3

        >>> run(drink(), drink('tea', 30), drink('water', 5))
        Start drinking coffee at 0
        Start drinking tea at 0
        Start drinking water at 0
        Done drinking water at 5
        Done drinking coffee at 20
        Done drinking tea at 30

.. content-tabs:: left-col

    As activities ``await`` notifications, activities are interleaved as if time would pass for real.
    By using the helpers of μSim, such as ``usim.time``, your activities naturally have the correct notifications.

Let's do more things...
-----------------------

.. content-tabs:: left-col

    So far, we have just started a fixed set of activities.
    Head over to the :doc:`next section <./02_stacked>` to combine several activities.
