.. usim documentation master file, created by
   sphinx-quickstart on Tue Mar 26 15:06:09 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

μSim - Lightweight Concurrent Simulations
=========================================

.. image:: https://readthedocs.org/projects/usim/badge/?version=latest
    :target: http://usim.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation

.. image:: https://img.shields.io/pypi/v/usim.svg
    :target: https://pypi.python.org/pypi/usim/
    :alt: Available on PyPI

.. image:: https://img.shields.io/github/license/MaineKuehn/usim.svg
    :target: https://github.com/MaineKuehn/usim/blob/master/LICENSE
    :alt: MIT Licensed

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3813587.svg
   :target: https://doi.org/10.5281/zenodo.3813587
   :alt: Cite with DOI

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Contents:

   source/tutorial/overview
   source/topics/overview
   source/api/usim
   source/api/usim.py
   source/glossary
   source/changelog

μSim is a discrete-event simulation framework
using the asynchronous programming features of Python.
It offers a lightweight and expressive user interface,
built on top of a powerful and robust simulation framework.

Using the ``async``/``await`` capabilities of Python3,
μSim allows you to both quickly and reliably build simulations,
no matter if they are small and simple, or large and complex.

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

To get started with some examples, check out the :doc:`source/tutorial/overview`.
If you have previously worked with SimPy_,
use our :doc:`source/topics/simpy` layer to quickly migrate your simulation.

Simple User Interface
---------------------

Writing simulations should not burden users with much technical jargon.
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
   async with until(time >= 3000) as scope:
      # complex tools are automatically managed
      async for message in stream:
         scope.do(handle(message))

To learn more about the μSim user interface,
check out the :doc:`source/api/usim` documentation.

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

.. _SimPy: https://simpy.readthedocs.io/
