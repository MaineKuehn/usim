from typing import Coroutine

from .__about__ import __version__
from ._core.loop import Loop as _Loop
from ._primitives.timing import Time, Eternity, Instant, each
from ._primitives.flag import Flag
from ._primitives.locks import Lock
from ._primitives.context import until, Scope, VolatileActivityExit
from ._primitives.activity import ActivityCancelled, ActivityState


__all__ = [
    'run',
    'time', 'eternity', 'instant', 'each',
    'until', 'Scope', 'ActivityCancelled', 'VolatileActivityExit', 'ActivityState',
    'Flag', 'Lock',
]


# User entry point
##################
def run(*activities: Coroutine, start: float = 0, till: float = None):
    """
    Run a simulation from the initial ``activities`` at time ``start`` until completion

    :param activities: initial activities of the simulation
    :param start: initial time of the simulation
    :param till: time at which to terminate the simulation
    """
    if till is not None:
        async def root(_activities=activities, _till=till):
            async with until(time == _till) as scope:
                for activity in _activities:
                    scope.do(activity)
        activities = root(_activities=activities, _till=till),
    loop = _Loop(*activities, start=start)
    loop.run()


# Time related singletons
#########################
time = Time()
eternity = Eternity()
instant = Instant()
