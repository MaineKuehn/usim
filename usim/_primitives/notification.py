from typing import List, Tuple, Coroutine
from contextlib import contextmanager

from .._core.loop import Hibernate, Interrupt, __LOOP_STATE__


# TODO: add protocol for destroying a notification


class NoSubscribers(Exception):
    ...


async def postpone():
    """
    Postpone a coroutine in the current time step

    This will safely requeue the current task,
    allowing other tasks to run and interrupts to occur.
    """
    task = __LOOP_STATE__.LOOP.activity
    wake_up = Interrupt('postpone', task)
    __LOOP_STATE__.LOOP.schedule(task, signal=wake_up)
    try:
        await Hibernate()
    except Interrupt as err:
        if err is not wake_up:
            assert task is __LOOP_STATE__.LOOP.activity, 'Break points cannot be passed to other coroutines'
            raise
    finally:
        wake_up.revoke()


@contextmanager
def subscribe(notification: 'Notification'):
    task = __LOOP_STATE__.LOOP.activity
    wake_up = Interrupt(notification, task)
    notification.__subscribe__(task, wake_up)
    try:
        yield
    except Interrupt as err:
        if err is not wake_up:
            assert task is __LOOP_STATE__.LOOP.activity, 'Break points cannot be passed to other coroutines'
            raise
    finally:
        notification.__unsubscribe__(task, wake_up)


class Notification:
    """
    Synchronisation point to which activities can subscribe

    .. code:: python

        await notification  # hibernate until notified

        async with until(notification):
            ...
    """
    __slots__ = ('_waiting',)

    def __init__(self):
        self._waiting = []  # type: List[Tuple[Coroutine, Interrupt]]

    def __await__(self):
        yield from self.__await_notification__().__await__()

    async def __await_notification__(self, interrupt: Interrupt = None):
        activity = __LOOP_STATE__.LOOP.activity
        interrupt = interrupt if interrupt is not None else Interrupt(self, activity)
        self.__subscribe__(activity, interrupt)
        try:
            await Hibernate()  # break point - we are resumed when the event is set
        except Interrupt as err:
            if err is not interrupt:  # resumed prematurely
                raise
        finally:
            self.__unsubscribe__(activity, interrupt)

    def __awake_next__(self) -> Tuple[Coroutine, Interrupt]:
        """Awake the oldest waiter"""
        try:
            waiter, interrupt = self._waiting.pop(0)
        except IndexError:
            raise NoSubscribers
        else:
            __LOOP_STATE__.LOOP.schedule(waiter, signal=interrupt)
            return waiter, interrupt

    def __awake_all__(self) -> List[Tuple[Coroutine, Interrupt]]:
        """Awake all waiters"""
        awoken = self._waiting.copy()
        self._waiting.clear()
        for waiter, interrupt in awoken:
            __LOOP_STATE__.LOOP.schedule(waiter, signal=interrupt)
        return awoken

    # Subscribe/Unsubscribe
    def __subscribe__(self, waiter: Coroutine, interrupt: Interrupt):
        """Subscribe a task to this notification, waking it when the notification triggers"""
        self._waiting.append((waiter, interrupt))

    def __unsubscribe__(self, waiter: Coroutine, interrupt: Interrupt):
        """Unsubscribe a subscribed task"""
        if interrupt.scheduled:
            interrupt.revoke()
        else:
            self._waiting.remove((waiter, interrupt))

    @contextmanager
    def __subscription__(self):
        task = __LOOP_STATE__.LOOP.activity
        wake_up = Interrupt(self, task)
        self.__subscribe__(task, wake_up)
        try:
            yield
        except Interrupt as err:
            if err is not wake_up:
                assert task is __LOOP_STATE__.LOOP.activity, 'Break points cannot be passed to other coroutines'
                raise
        finally:
            self.__unsubscribe__(task, wake_up)

    def __del__(self):
        if self._waiting:
            raise RuntimeError('%r collected without releasing %d waiting tasks:\n  %s' % (
                self, len(self._waiting), self._waiting))

    def __repr__(self):
        return '<%s, waiters=%d>' % (self.__class__.__name__, len(self._waiting))
