=======================
μSim -- Simply Simulate
=======================

μSim offers a lightweight and expressive user interface,
built on top of a powerful and robust simulation framework.
Using the ``async``/``await`` capabilities of Python3,
μSim allows you to both quickly and reliably build even complex simulations.

.. code:: python3

   >>> from usim import delay, run
   >>>
   >>> async def metronome(period: float, sound: str):
   ...     async for now in delay(period):
   ...         print(sound, '@', now)
   ...
   >>> run(metronome(period=1, sound='tick'), metronome(period=2, sound='TOCK'), till=5)
   tick @ 1
   TOCK @ 2
   tick @ 2
   tick @ 3
   TOCK @ 4
   tick @ 4
   tick @ 5

Check out `the μSim documentation <https://usim.readthedocs.io/en/latest/>`_
for more information on creating simulations with μSim.

μSim Development
================

If you are reading this, you are looking at
`the μSim repository <https://github.com/MaineKuehn/usim>`_.
Here you can find the current development version,
submit issue tickets, or propose pull requests.

In order to try the most recent development version,
check out and install the ``master`` branch.
This branch is guaranteed to contain only working changes.

If you want to report issues or propose changes, please take a look at the
`contribution guidelines <https://github.com/MaineKuehn/usim/blob/master/CONTRIBUTING.md>`_.
