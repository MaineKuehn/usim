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

Non-Events?
+++++++++++

Is there a need for a "raw" event? I.e. just `await` API?
Non-bare events would support composition and interrupts:

.. code:: python

    # primitive wait
    event = time(20)              # primitive event
    await event
    event = time(20) & proc.done  # composed event
    await event

Toggle Event
++++++++++++

Allow Events to react to toggling either way. I.e. something like

.. code:: python

    await event         # resume if True
    await event.true    # resume if True
    await event.false   # resume if False
    await invert(event) # resume if False

Context meaning
+++++++++++++++

Have a consistent meaning of contexts? E.g. "set", "if set" (event), "exclusive set" (lock)

.. code:: python

    with lock:  # acquire lock, proceed if set succeeds
        ...

    with event:  # set event?
        ...

`await` for events, `async with` for interrupts?

.. code:: python

    await event        # resume if True

    async with event:  # interrupt if False
        ...

Channels
++++++++

Unbuffered message passing - every `await channel.send(message)` wakes up all `message = await channel` waiters.
Can also be used as async iterator:

.. code:: python

    # await gives next message
    message = await channel
    message = await anext(channel)

    # async for gives all messages
    async for message in channel:
        ...

Should it be `await channel.send` (Queue) or `await channel.asend` (async generator, PEP0525)?
How about `await channel.broadcast`, `await channel.push`, `await channel.put`?
Separate one-to-one and one-to-many per Channel types?
