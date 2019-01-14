from typing import List, Tuple, Coroutine

from ..core import Hibernate, Interrupt as CoreInterrupt, GetTask, Schedule


class NoSubscribers(Exception):
    ...


async def postpone():
    """
    Postpone a coroutine in the current time step

    This will safely requeue the current task,
    allowing other tasks to run and interrupts to occur.
    """
    task = await GetTask()
    wake_up = CoreInterrupt('postpone', task)
    await Schedule(task, signal=wake_up)
    try:
        await Hibernate()
    except CoreInterrupt as err:
        if err is not wake_up:
            if wake_up.scheduled:
                wake_up.revoke()
            assert task is await GetTask(), 'Break points cannot be passed to other coroutines'
            raise
    except BaseException:
        if wake_up.scheduled:
            wake_up.revoke()
        raise


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
        self._waiting = []  # type: List[Tuple[Coroutine, Exception]]

    def __await__(self):
        interrupt = CoreInterrupt((self, id(self)))
        task = yield from GetTask().__await__()
        yield from self.__subscribe__(interrupt, task).__await__()
        try:
            yield from Hibernate().__await__()  # break point - we are resumed when the event is set
        except CoreInterrupt as err:
            if err is not interrupt:  # resumed prematurely
                if interrupt.scheduled:
                    interrupt.revoke()
                else:
                    yield from self.__unsubscribe__(interrupt, task).__await__()
                raise
        except BaseException:
            if interrupt.scheduled:
                interrupt.revoke()
            else:
                yield from self.__unsubscribe__(interrupt, task).__await__()
            raise

    async def __trigger__(self):
        """Trigger the notification, waking up waiting tasks"""
        raise NotImplementedError("Notification implementations must implement a '__trigger__' method")

    async def __awake_next__(self) -> Tuple[Coroutine, Exception]:
        """Awake the oldest waiter"""
        try:
            waiter, interrupt = self._waiting.pop(0)
        except IndexError:
            raise NoSubscribers
        else:
            await Schedule(waiter, signal=interrupt)
            return waiter, interrupt

    async def __awake_all__(self) -> List[Tuple[Coroutine, Exception]]:
        """Awake all waiters"""
        awoken = self._waiting.copy()
        self._waiting.clear()
        for waiter, interrupt in awoken:
            await Schedule(waiter, signal=interrupt)
        return awoken

    async def __subscribe__(self, interrupt: CoreInterrupt, task: Coroutine = None):
        """Subscribe a task to this notification, waking it when the notification triggers"""
        waiter = task if task is not None else (await GetTask())
        self._waiting.append((waiter, interrupt))

    async def __unsubscribe__(self, interrupt: CoreInterrupt, task: Coroutine = None):
        """Unsubscribe a subscribed tasks"""
        waiter = task if task is not None else (await GetTask())
        self._waiting.remove((waiter, interrupt))

    def __del__(self):
        if self._waiting:
            raise RuntimeError('%r collected without releasing %d waiting tasks:\n  %s' % (
                self, len(self._waiting), self._waiting))

    def __repr__(self):
        return '<%s, waiters=%d>' % (self.__class__.__name__, len(self._waiting))


class Anycast(Notification):
    """
    Notification that awakes one waiter every time it is triggered
    """
    __slots__ = ()

    async def __trigger__(self):
        try:
            waiter, interrupt = self._waiting.pop(0)
        except IndexError:
            return
        else:
            await Schedule(waiter, signal=interrupt)


class Broadcast(Notification):
    """
    Notification that awakes all waiters every time it is triggered
    """
    __slots__ = ()

    async def __trigger__(self):
        for waiter, interrupt in self._waiting:
            await Schedule(waiter, signal=interrupt)
        self._waiting.clear()
