##############
Draft for μsim
##############

This is a draft for a mikro simulation framework.
It builds on a kernel that runs several coroutines.
The passing of time and interaction between coroutines is purely simulated.

Selling Points
##############

* lean and user-friendly API
* clear ``await`` and ``async def`` syntax
    * consistent ``await``-means-interrupt story
    * powerful ``async with`` and ``async for`` blocks
* Fully event-driven API to intuitively express flow of time and relations
    * intuitively create, await and trigger events
    * easily synchronise on actions, conditions and constraints
* automatic Environment handling

Notes
#####

Performance
-----------

PyPy is currently ~3 times faster for large (~5000 steps) repetitions.

Usage
-----

Resolution
++++++++++

Works but leads to time drifts:
sleep for 3 * 1.5 at 0.2 gives 4.8 instead of 4.5.
Sensitive to alignment, works well if (sleep % resolution) ~ 0
Not suitable if people want to simulate actual time.

Possible approaches:

Tracked Deadline
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

Conclusion
~~~~~~~~~~

Dropped time resolution entirely, in favour of an arbitrary precision clock.
Time semantics have been improved, making it simple to do time-scoped actions.

.. code:: python

    async for now in each(interval=20):
        ...

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

Conclusion
~~~~~~~~~~

Using FIFO and a time -> turn based schedule.
All primitives requeue for the current time step in ``await`` expressions.

The current time uses a turn queue separate from the time schedule.
Re-queuing puts a task at the end of the turn queue.
The loop runs tighter around the turn-queue, avoiding time and schedule overhead.

API/Implementation
++++++++++++++++++

Probably a good idea to separate API and Loop implementation.

Conclusion
~~~~~~~~~~

Using a low-level (loop), intermediate-level (notifications) and high-level (api) layer.
The notification and api layer are somewhat intertwined for implementation simplicity;
notifications are abstract and exposed as type hints for users.

API Design
----------

Non-Await Communication
+++++++++++++++++++++++

Using only `await` to communicate with the event loop has some ugly side-effects for *non-async* operations.
For example, querying the time or coroutine *look* like they postpone execution, but don't.

.. code:: python

    now = await time        # query time
    await (time + 20)       # postpone
    now = await (time + 20) # postpone and query

This is doubly confusing when we do a query somewhere deep in an API which is otherwise sync.
There we need `await` only for communication, but the operation is not truly async.
That also means delayed interrupts (`async with until(...):`) *may or may not* fire at an `await`.

Ideally, we use `await` (`async with`, ...) *only* for true break points, i.e. whenever an interrupt can occur.
Otherwise, communicate via a side-channel, such as global/thread-local loop reference.

Conclusion
~~~~~~~~~~

Split ``await`` and loop commands into separate category.
An ``await`` is only needed for actions that suspend the current coroutine.

An ``await`` always causes postponement, even if it is just in the same time step.
Many actions, such as scheduling, are no longer ``await`` to compensate this.

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

Conclusion
~~~~~~~~~~

All "conditional" events follow the ``Condition`` API, which allows composition.
This includes time.

Toggle Event
++++++++++++

Allow Events to react to toggling either way. I.e. something like

.. code:: python

    await event         # resume if True
    await event.true    # resume if True
    await event.false   # resume if False
    await invert(event) # resume if False
    await ~event        # resume if False

Conclusion
~~~~~~~~~~

All "conditional" events follow the ``Condition`` API, which allows inversion.

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

Separate context to mark kind of signal?

    async with lock:   # regular "get this resource" context
        ...

    async with until(lock):  # explicit "interrupt when triggered" context
        ...

Conclusion
~~~~~~~~~~

Bare ``async with`` is for acquiring resources (locks).
Others use explicit calls, as in ``until(notification)``.

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

Conclusion
~~~~~~~~~~

Streams are separated into broadcast and anycast by type.
Sending is always via `await channel.put`.

Locks
+++++

Can we detect deadlocks? Something like tracking the stack of Locks, and raising an error on conflicts?

Say we have activity A try and acquire Locks `x->y->z` and B Locks `x->z->y`, and both have the first two.
When A queues for `z`, it just suspends. But when B now queues for `y`, it detects:
- the owner will not release `y` before acquiring `z`
- I will not release `z` before acquiring `y`
- Deadlock
