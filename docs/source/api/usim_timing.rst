Working with simulated time
===========================

.. toctree::
   :hidden:

The primary tool to work with time in a simulation is :py:data:`usim.time`.
It gives access to the current time, and using it in expressions provides
:py:class:`~usim.typing.Condition`\ s to check or ``await`` the passing of time.
For convenience and readability, several helpers are provided:
:py:data:`usim.eternity` and :py:data:`usim.instant` are the longest and shortest
delay possible, respectively.
:py:func:`usim.delay` and :py:func:`usim.interval` allow to repeatedly delay
in order to act at fixed intervals.

Direct Interaction with Time
----------------------------

.. autodata:: usim.time
    :annotation:

Actively Postpone and Suspend
-----------------------------

.. autodata:: usim.eternity
    :annotation:

.. autodata:: usim.instant
    :annotation:

Controlled Repetitions
----------------------

.. autofunction:: usim.interval
    :async-for:

.. autofunction:: usim.delay
    :async-for:
