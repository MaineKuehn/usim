from typing import List, Tuple, Coroutine
from contextlib import contextmanager

from .._core.loop import Interrupt, __LOOP_STATE__, __HIBERNATE__


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
        await __HIBERNATE__
    except Interrupt as err:
        if err is not wake_up:
            assert (
                task is __LOOP_STATE__.LOOP.activity
            ), 'Break points cannot be passed to other coroutines'
            raise
    finally:
        wake_up.revoke()


async def suspend(*, delay: float, until: float):
    """
    Suspend a coroutine until a future time step

    This will safely requeue the current task,
    allowing other tasks to run and interrupts to occur.
    Time will pass as if ``time == until`` or ``time + delay``
    were used, but there is no ``Condition`` interface on top.
    """
    task = __LOOP_STATE__.LOOP.activity
    wake_up = Interrupt('postpone', task)
    __LOOP_STATE__.LOOP.schedule(task, signal=wake_up, delay=delay, at=until)
    try:
        await __HIBERNATE__
    except Interrupt as err:
        if err is not wake_up:
            assert (
                task is __LOOP_STATE__.LOOP.activity
            ), 'Break points cannot be passed to other coroutines'
            raise
    finally:
        wake_up.revoke()


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
        with self.__subscription__():
            yield from __HIBERNATE__

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
        """Subscribe a task to this notification"""
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
                assert (
                    task is __LOOP_STATE__.LOOP.activity
                ), 'Break points cannot be passed to other coroutines'
                raise
        finally:
            self.__unsubscribe__(task, wake_up)

    if __debug__:
        def __del__(self):
            if self._waiting:
                raise RuntimeError(
                    '%r collected without releasing %d waiting tasks:\n  %s' % (
                        self, len(self._waiting), self._waiting
                    )
                )

    def __repr__(self):
        return '<%s, waiters=%d>' % (self.__class__.__name__, len(self._waiting))
