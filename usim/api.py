import collections
from typing import Coroutine, Awaitable, TypeVar

from .core import run, Schedule, Hibernate, GetTime, GetTask, Task


__all__ = ['run', 'time', 'spawn', 'FifoLock', 'FifoEvent']


#: Yield Type of a Coroutine
YT = TypeVar('YT')
#: Send Type of a Coroutine
ST = TypeVar('ST')
#: Return Type of a Coroutine
RT = TypeVar('RT')


async def _chain(*coroutines):
    result = None
    for coro in coroutines:
        result = await coro
    return result


async def time(after: float = None, *, at: float = None) -> Awaitable[float]:
    """
    Wait until an absolute or relative point in time

    :param after: time span to wait for
    :param at: point in time to wait for
    :return: time at which the waiting completed

    Both parameters can be given as keyword arguments;
    as a shorthand, ``span`` may also be given as an unnamed argument.
    Only one of ``span`` or ``at`` may be used at once.

    Always returns the current time at which action is resumed.
    If no parameters are given, directly returns the current time.

    .. code:: python

        # wait until a point in time
        await time(at=1986)
        # wait for a duration to pass
        await time(delay=60*60*24)
        await time(60)
        # get the current time
        await time()
    """
    if after is at is None:
        return await GetTime()
    assert after is None or at is None, "only one of 'after' or 'at' may be used"
    if after is not None:
        await Schedule(delay=after)
    else:
        await Schedule(delay=(at - await GetTime()))
    await Hibernate()
    return await GetTime()


async def spawn(coroutine: Coroutine[YT, ST, RT], after: float = None, at: float = None) -> Awaitable[RT]:
    if after is at is None:
        return await Schedule(Task(coroutine))
    assert after is None or at is None, "only one of 'after' or 'at' may be used"
    if after is not None:
        return await Schedule(Task(coroutine), delay=after)
    else:
        return await Schedule(Task(coroutine), delay=(at - await GetTime()))


class FifoLock(object):
    """
    Lock owned by only one Execution

    .. code:: python

        async with lock:
            await time(delay=120)
    """
    def __init__(self):
        self.held = False
        self._waiters = collections.deque()

    async def __aenter__(self):
        # uncontested - just take it
        if not self.held:
            self.held = True
            return
        # contested - store THIS STACK for resumption
        self._waiters.append(await GetTask())
        await Hibernate()  # break point - we are resumed when we own the lock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # pass on lock state to next waiter
        try:
            waiter = self._waiters.popleft()
        except IndexError:
            self.held = False
        else:
            await Schedule(waiter)
        # pass on any errors
        return False

    def __del__(self):
        if self.held and self._waiters:
            raise RuntimeError('%r blocks waiters but was never released' % self)

    def __repr__(self):
        return '<%s, held=%s, waiters=%d>' % (self.__class__.__name__, self.held, len(self._waiters))


class FifoEvent(object):
    def __init__(self):
        self._value = False
        self._waiters = []

    def __bool__(self):
        return self._value

    def __await__(self):
        """Await that this Event is set"""
        if self._value:
            return
        # unset - store THIS STACK for resumption
        stack = yield from GetTask().__await__()
        self._waiters.append(stack)
        yield Hibernate().__await__()  # break point - we are resumed when the event is set

    async def set(self):
        self._value = True
        for waiter in self._waiters:
            await Schedule(waiter)
        self._waiters.clear()

    async def clear(self):
        self._value = False

    async def broadcast(self):
        await self.set()
        await self.clear()

    def __repr__(self):
        return '<%s, set=%s, waiters=%d>' % (self.__class__.__name__, self._value, len(self._waiters))

