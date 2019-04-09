.. usim documentation master file, created by
   sphinx-quickstart on Tue Mar 26 15:06:09 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

μSim - Simulations for Humans
=============================

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   source/tutorial/overview
   source/glossary
   source/api/modules

μSim offers a lightweight and expressive user interface,
built on top of a powerful and robust simulation framework.
Using the ``async``/``await`` capabilities of Python3,
μSim allows you to both quickly and reliably build even complex simulations.

.. code:: python3

   >>> from usim import each, run
   >>>
   >>> async def metronome(period: float, sound: str):
   ...     async for now in each(delay=period):
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

Simple User Interface
---------------------

Writing simulations with μSim should burden users with as little technical jargon as possible.
We want you to focus on your simulation, not on our implementation.
You can do most things with regular operations and expressions.
Using ``await`` and ``async`` is only needed to synchronise activities.

.. code:: python3

   # *wait* for 20 time units
   await (time + 20)

   # *wait* for a point in time
   await (time == 1999)

   # *check* if a point in time is met already
   if time < 2001:
      ...

Asynchronous programming is a complex task, and asynchronous simulations are as well.
We cannot prevent every error - but we strive to make writing correct code as pleasant as possible.
All hard-to-use functionality is automatically scoped and managed, making it natural to do the right thing.

.. code:: python3

   # scoping is a builtin concept of usim
   async with out(time >= 3000) as scope:
      # complex tools are automatically managed
      async for message in stream:
         scope.do(handle(message))

Powerful Foundation
-------------------

Under the hood, μSim implements a fully-featured, interrupt-based coroutine scheduler.
Its inner working and principles are inspired by modern multi-tasking libraries
such as :py:mod:`asyncio`, :py:mod:`trio` and others.
By focusing solely on simulation, μSim achieves lightweight and high-performing event handling.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`