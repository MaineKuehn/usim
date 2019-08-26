"""
SimPy to μSim compatibility layer
=================================

This package and its submodules emulate the API of the :py:mod:`simpy` package.
It serves as a drop-in replacement for SimPy in order to gradually integrate
and migrate simulations to μSim. To use the emulated API in an existing simulation,
it is sufficient to import ``usim.py`` in place of ``simpy``.

.. code:: python3

    # load the compatibility layer in place of simpy
    import usim.py as simpy

The ``usim.py`` package itself provides direct access to the most relevant objects.
However, they can be fetched from their respective submodules as well.

Environments (:py:mod:`usim.py.core`)
-------------------------------------

{environments_table}

.. hint::

    μSim simulations are started by :py:func:`usim.run`.

Events (:py:mod:`usim.py.events`)
---------------------------------

{events_table}

.. hint::

    μSim simulations can ``await`` events and may
    :py:meth:`~usim.py.events.Event.succeed` and :py:meth:`~usim.py.events.Event.fail`
    them.


Resources
---------

``usim.py`` implements no resources yet.

Exceptions (:py:mod:`usim.py.exceptions`)
-----------------------------------------

{exceptions_table}
"""
from typing import Union, Tuple
from .core import Environment
from .exceptions import Interrupt, SimPyException, StopProcess
from .events import Event, Timeout, Process, AllOf, AnyOf

__all__ = ['Environment', 'Interrupt', 'Event', 'Timeout', 'Process', 'AllOf', 'AnyOf']


def _api_table(*members: Tuple[Union[type, str], str, str]):
    table_content = []
    table_size = 0, 0
    for obj, signature, description in members:
        if isinstance(obj, str):
            element = (
                rf'``{obj}``\ {signature}',
                description,
            )
        else:
            tp = ':py:exc:' if isinstance(obj, BaseException) else ':py:class:'
            element = (
                rf'{tp}`~{obj.__module__}.{obj.__qualname__}`\ {signature}',
                description,
            )
        table_size = max(table_size[0], len(element[0])),\
            max(table_size[1], len(element[1]))
        table_content.append(element)
    doc = f"{'=' * table_size[0]} {'=' * table_size[1]}\n"
    doc += ''.join(
        head.ljust(table_size[0]) + ' ' + description.ljust(table_size[1]) + '\n'
        for head, description in table_content
    )
    doc += f"{'=' * table_size[0]} {'=' * table_size[1]}\n"
    return doc


__doc__ = __doc__.format(
    environments_table=_api_table(
        (Environment, '(initial_time=0)', 'Execution environment for a simulation'),
        ('RealtimeEnvironment', '(...)', 'Not supported by μSim'),
    ),
    events_table=_api_table(
        (Event, '(env)', 'Event that is manually triggered'),
        (
            Timeout, '(env, delay, value=None)',
            'Event that triggers after a ``delay``',
        ),
        (
            Process, '(env, generator)',
            'Active event that processes an event yielding generator',
        ),
        (
            AllOf, '(env, events)',
            'Event that triggers once all ``events`` succeed',
        ),
        (
            AnyOf, '(env, events)',
            'Event that triggers once any ``events`` succeed',
        ),
        (
            Interrupt, '(cause)',
            'Exception to :py:meth:`~usim.py.events.Process.interrupt` a Process',
        ),
    ),
    exceptions_table=_api_table(
        (
            SimPyException, '()',
            'Base case for all non-internal exceptions',
        ),
        (
            Interrupt, '(cause)',
            'Exception to :py:meth:`~usim.py.events.Process.interrupt` a Process',
        ),
        (
            StopProcess, '(value)',
            'Exception to :py:meth:`~usim.py.core.Environment.exit` a Process',
        ),
    ),
)
