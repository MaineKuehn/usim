from typing import Coroutine, Awaitable

from ..core import GetTime, Schedule, Interrupt as CoreInterrupt

from .notification import Broadcast
from .condition import Condition


async def relative_time(at: float) -> float:
    return at - await GetTime()


# TODO: fix correct but idiotic naming


_GET_TIME = GetTime()


class Soonest(Broadcast, Condition):
    """
    Condition that triggers once a point in time has been observed

    :note:  :py:class:`Soonest` can only observe time once used in an
            `await` expression or `async with` context. Otherwise,
            its boolean value remains False indefinitely.
    """
    def __init__(self, point: float):
        super().__init__()
        self.point = point
        self._observer = None
        self._observed = False

    def __bool__(self):
        return self._observed

    def __invert__(self):
        raise NotImplementedError("Inverting a Soonest")  # technically possible, but is this ever the right thing?

    async def _ensure_observer(self):
        # there is nothing to do at all
        if self._observed or self._observer:
            return self._observed
        # see if we can get done fast
        if await GetTime() >= self.point:
            self._observed = True
        else:
            await Schedule(self._observe(), delay=await relative_time(self.point))
        return self._observed

    async def _observe(self):
        self._observed = True
        await self.__trigger__()

    def __await__(self):
        print('await', self)
        if (yield from self._ensure_observer().__await__()):
            return True
        return (yield from super().__await__())

    async def __subscribe__(self, interrupt: CoreInterrupt, task: Coroutine = None):
        await self._ensure_observer()
        return await super().__subscribe__(interrupt, task)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.point)


class Every:
    def __init__(self, interval: float):
        self.interval = interval

    async def __anext__(self):
        await Soonest(await GetTime() + self.interval)
        return await GetTime()


def every(interval: float):
    return Every(interval)


class Time:
    """
    Representation of simulation time

    .. code:: python

        now = await time  # get the current time
        then = await (time + 20)  # wait for a time span to pass
        partytime = await (time == 1999)  # wait for a time date to occur

        async with until(time + 20):  # abort block after a delay
            ...

        async with until(time == 1999):  # abort block at a fixed time
            await party()
    """
    def __await__(self) -> Awaitable[float]:
        yield from _GET_TIME.__await__()

    def __add__(self, other):
        pass


time = Time()
