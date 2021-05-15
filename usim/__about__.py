"""
===========================
``usim`` -- Simply Simulate
===========================

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
for more information.
"""
__title__ = 'usim'
__summary__ = 'Lightweight Simulation Framework'
__url__ = 'https://github.com/MaineKuehn/usim'

__version__ = '0.4.4'
__author__ = 'Eileen Kuehn, Max Fischer'
__email__ = 'mainekuehn@gmail.com'
__copyright__ = '2019 %s' % __author__
__keywords__ = 'simulation simpy event loop async coroutine'
