##############
Draft for μsim
##############

This is a draft for a mikro simulation framework.
It builds on a kernel that runs several coroutines.
The passing of time and interaction between coroutines is purely simulated.

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

    * Track time drift per Task. Add/subtract whenever we have a full resolution offset.

    * Separate Sleep (time, exact) and Delay (steps, resolution) commands.

    * Single Sleep command with ``strict: bool`` flag.

    * Explicit "on average X second sleep" loop or context.

        .. code:: python

            async for now in every(10):
                print(now, 'should be roughly 10s later')
