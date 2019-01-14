from typing import Union, Coroutine, List, TypeVar, Any
from functools import singledispatch

from ..core import GetTask, Interrupt as CoreInterrupt, Schedule
from .notification import Broadcast, Anycast
from .activity import Activity
from .delay import relative_time


RT = TypeVar('RT')


class WaitScope:
    """
    Scope that waits for all branched off tasks on exit
    """
    def __init__(self):
        self._children = []  # type: List[Activity]

    # TODO: add daemon flag for expendable children
    async def branch(self, payload: Coroutine[Any, Any, RT], *, after: float = None, at: float = None) -> Activity[RT]:
        child_activity = Activity(payload)
        if after is None and at is None:
            delay = 0
        elif after is not None:
            delay = after
        elif after is None:
            delay = await relative_time(at)
        else:
            raise ValueError("at least one of 'after' or 'at' must be None")
        await Schedule(
            child_activity.__runner__(),
            delay=delay,
        )
        self._children.append(child_activity)
        return child_activity

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for child in self._children:
            await child
        return False


class CancelScope(WaitScope):
    """
    Scope that cancels all branched off tasks on exit
    """
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for child in self._children:
            await child.cancel()
        return await super().__aexit__(exc_type, exc_val, exc_tb)


class InterruptScope(CancelScope):
    """
    Context that is interrupted on notification

    :see: :py:func:`~.until`
    """
    __slots__ = ('_notification', '_interrupt', '_task')

    def __init__(self, notification: Union[Broadcast, Anycast]):
        super().__init__()
        self._notification = notification
        self._interrupt = CoreInterrupt((notification, id(self)))
        self._task = None

    async def __aenter__(self):
        if self._task is not None:
            raise RuntimeError('%r is not re-entrant' % self)
        self._task = await GetTask()
        await self._notification.__subscribe__(self._interrupt, self._task)
        return super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is CoreInterrupt and exc_val is self._interrupt:
            await super().__aexit__(exc_type, exc_val, exc_tb)
            return True
        if self._interrupt.scheduled:
            self._interrupt.revoke()
        else:
            await self._notification.__unsubscribe__(self._interrupt, self._task)
        await super().__aexit__(exc_type, exc_val, exc_tb)
        return False


@singledispatch
def until(notification: Union[Broadcast, Anycast]):
    """
    Context that is interrupted on notification

    An asynchronous `until`-context listens for a notification *without* stopping execution.
    This allows notification on any break point (usually an `await`) in the context.

    .. code:: python

        async with until(done):
            await delay(math.inf)

    :note: A break point in the context is always required,
           even when the notification would trigger immediately.
    """
    return InterruptScope(notification)
