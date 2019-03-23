from typing import Coroutine

from ._core.loop import Loop as _Loop
from ._primitives.timing import Time, Eternity, Instant, each
from ._primitives.flag import Flag
from ._primitives.locks import Lock
from ._primitives.context import until, Scope
from ._primitives.activity import ActivityCancelled


__all__ = ['run', 'time', 'eternity', 'instant', 'each', 'until', 'Scope', 'Flag', 'Lock', 'ActivityCancelled']


# User entry point
##################
def run(*activities: Coroutine, start: float = 0):
    """
    Run a simulation from the initial ``activities`` at time ``start`` until completion

    :param activities: initial activities of the simulation
    :param start: initial time of the simulation
    """
    loop = _Loop(*activities, start=start)
    loop.run()


# Time related singletons
#########################
time = Time()
eternity = Eternity()
instant = Instant()
