Getting Active
==============

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

Time in a Nutshell
------------------

For this example, we use μSim's time manipulation capabilities.
Using ``usim.time``,
you can query the current simulation time
and
suspend an activity for some time.

.. code:: python3

    # make time accessible
    from usim import time

    # access current time value
    print(time.now)

    # delay in an activity
    await (time + 20)
    await (time == 1999)

That's it - you know how to manipulate time now.
Just keep in mind these only work during a simulation.

Lesson 01: Defining an Activity
-------------------------------
