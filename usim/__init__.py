from typing import Coroutine

from .__about__ import __version__  # noqa: F401
from ._core.loop import Loop as _Loop
from ._primitives.timing import Time, Eternity, Instant, interval, delay
from ._primitives.flag import Flag
from ._primitives.locks import Lock
from ._primitives.context import until, Scope, VolatileTaskClosed
from ._primitives.task import TaskCancelled, TaskState, TaskClosed, CancelTask
from ._primitives.concurrent_exception import Concurrent
from ._basics.streams import Channel, Queue, StreamClosed
from ._basics.tracked import Tracked
from ._basics.resource import Capacities, Resources, ResourcesUnavailable


__all__ = [
    'run',
    'time', 'eternity', 'instant', 'interval', 'delay',
    'until', 'Scope',
    'TaskCancelled', 'VolatileTaskClosed', 'TaskClosed', 'TaskState', 'CancelTask',
    'Concurrent',
    'Flag', 'Tracked',
    'Lock',
    'Channel', 'Queue', 'StreamClosed',
    'Capacities', 'Resources', 'ResourcesUnavailable',
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
