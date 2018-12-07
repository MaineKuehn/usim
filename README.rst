##############
Draft for μsim
##############

This is a draft for a mikro simulation framework.
It builds on a kernel that runs several coroutines.
The passing of time and interaction between coroutines is purely simulated.

Selling Points
##############

* clear ``await`` and ``async def`` syntax
    * allows using ``async with`` and ``async for`` blocks
* automatic Environment handling

Notes
#####

Performance
-----------

PyPy is ~3 times faster for large (~5000 steps) repetitions.

Usage
-----

Resolution
++++++++++

Works but leads to time drifts:
sleep for 3 * 1.5 at 0.2 gives 4.8 instead of 4.5.
Sensitive to alignment, works well if (sleep % resolution) ~ 0
Not suitable if people want to simulate actual time.

Possible approaches:

Tracked Time
    Track time drift per Task. Add/subtract whenever we have a full resolution offset.

Separate Interfaces
    Separate Sleep (time, exact) and Delay (steps, resolution) commands.

Strictness Flags
    Single Sleep command with ``strict: bool`` flag.

Drift Scope
    Explicit "on average X second sleep" loop or context.

    .. code:: python

        async for now in every(10):
            print(now, 'should be roughly 10s later')

Re-Scheduling Priority
++++++++++++++++++++++

Several actions communicate with the event loop but may resume afterwards:
``await schedule(child)`` finishes immediately, while the point of ``await now`` is to resume.
The question is how to re-schedule after an infinitesimal interruption, when other routines must be scheduled as well.

Random Order (``trio``)
    Resume an arbitrary routine from the waiting area.
    This is motivated (``trio``) by not picking a scheme to prevent reliance on it and thus risk feature lock-in.

Resume First
    Resume the routine that has interrupted.
    Best turnaround (switching can be handled outside the event loop) but not truly async.

Resume Last
    Resume the routine that has waited the longest.

API/Implementation
++++++++++++++++++

Probably a good idea to separate API and Loop implementation.

Primitives
----------

Toggle Event
++++++++++++

Allow Events to react to toggling either way. I.e. something like

.. code:: python

    await event
    await event.true
    await event.false

Context meaning
+++++++++++++++

Have a consistent meaning of contexts? E.g. "set", "if set" (lock), "exclusive set" (lock)

.. code:: python

    with lock:  # acquire lock, proceed if set succeeds
        ...

    with event:  # set event?
        ...
