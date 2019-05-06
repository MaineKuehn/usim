from typing import Coroutine

from .._core.loop import __LOOP_STATE__
from .notification import Notification, NoSubscribers


class Lock:
    """
    Synchronization primitive that may be acquired by only one Activity at a time

    Locks enforce mutually exclusive access for Activities,
    by allowing only one owner at any time.
    Activities can acquire ownership of a :py:class:`~.Lock` only via an
    ``async with`` context, and automatically release when exiting the block:

    .. code:: python

        async with lock:
            ...

    Ownership of a lock is inherently tied to a specific :term:`activity`;
    it is not possible to acquire and release a :py:class:`~.Lock`
    across several activities.
    Every lock is re-entrant for its owning :term:`activity`:
    an Activity can acquire the same lock multiple times.
    This allows using Locks safely in recursive calls.
    """
    __slots__ = ('_notification', '_owner', '_depth')

    def __init__(self):
        self._notification = Notification()
        self._owner = None  # type: Coroutine
        self._depth = 0

    @property
    def available(self) -> bool:
        """
        Check whether the current Task can acquire this lock

        Entering a :py:class:`~.Lock` in its context manager does not allow
        backing off when the :py:class:`~.Lock` cannot be acquired.
        Availability of a :py:class:`~.Lock` should be checked if it shall
        only be acquired when available.

        .. code:: python3

            if lock.available:  # only acquire lock if possible
                with lock:
                    ...
            else:
                ...
        """
        if self._owner is None:
            return True
        else:
            return self._owner is __LOOP_STATE__.LOOP.activity

    async def __aenter__(self):
        current_activity = __LOOP_STATE__.LOOP.activity
        if self._owner is None:
            self._owner = current_activity
        elif self._owner is not current_activity:
            try:
                await self._notification
            except BaseException:
                # we are the designated owner, pass on ownership
                if self._owner == current_activity:
                    self.__release__()
                raise
        self._depth += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert exc_type is GeneratorExit or self._owner == __LOOP_STATE__.LOOP.activity
        self._depth -= 1
        if self._depth == 0:
            self.__release__()
        return False

    def __release__(self):
        try:
            candidate, signal = self._notification.__awake_next__()
        except NoSubscribers:
            self._owner = None
        else:
            self._owner = candidate

    def __repr__(self):
        return '<%s, owner=%s, depth=%s>' % (
            self.__class__.__name__, self._owner, self._depth
        )

    if __debug__:
        def __enter__(self):
            raise AttributeError(
                "Lock does not implement '__enter__'\n\n"
                "A lock cannot be acquired in a regular context.\n"
                "Use an 'async with' context instead."
            )

        def __exit__(self):
            raise AttributeError(
                "Lock does not implement '__exit__'\n\n"
                "A lock cannot be acquired in a regular context.\n"
                "Use an 'async with' context instead."
            )
