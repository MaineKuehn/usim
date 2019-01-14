from typing import Coroutine

from ..core import GetTask
from .notification import Notification, NoSubscribers


class Lock:
    """
    Synchronization primitive that may be acquired by only one Activity at a time

    Locks enforce mutually exclusive access for Activities,
    by allowing only one owner at any time.
    Activities can acquire ownership of a Lock only via an ``async with`` context:

    .. code:: python

        async with lock:
            ...

    Locks are re-entrant:
    an Activity can acquire the same lock multiple times.
    This allows using Locks safely in recursive calls.
    """
    def __init__(self):
        self._notification = Notification()
        self._owner = None  # type: Coroutine
        self._depth = 0

    @property
    async def peek(self):
        """
        Check whether the current Activity can acquire this lock
        """
        if self._owner is None:
            return True
        elif self._owner is await GetTask():
            return True
        else:
            return False

    async def __aenter__(self):
        current_activity = await GetTask()
        if self._owner is None:
            self._owner = current_activity
        elif self._owner is not current_activity:
            try:
                await self._notification
            except BaseException:
                # we are the designated owner, pass on ownership
                if self._owner == current_activity:
                    await self.__release__()
                raise
        self._depth += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self._owner == await GetTask()
        self._depth -= 1
        if self._depth == 0:
            await self.__release__()
        return False

    def __block__(self, by):
        """Prevent the lock from being acquired"""
        assert self._owner is None or self._owner is by, 'cannot block an owned lock'
        self._owner = by

    async def __release__(self):
        try:
            candidate, signal = self._notification.__awake_next__()
        except NoSubscribers:
            self._owner = None
        else:
            self._owner = candidate

    def __repr__(self):
        return '<%s, owner=%s, depth=%s>' % (self.__class__.__name__, self._owner, self._depth)
