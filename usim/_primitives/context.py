from typing import Coroutine, List, TypeVar, Any

from .._core.loop import __LOOP_STATE__, Interrupt as CoreInterrupt
from .notification import Notification
from .flag import Flag
from .activity import Activity


RT = TypeVar('RT')


class Scope:
    """
    Synchronisation range for new and existing activities

    .. code:: python

        async with Scope() as scope:
            scope.do(show_clock, volatile=True)
    """
    __slots__ = ('_children', '_done', '_activity', '_volatile_children')

    def __init__(self):
        self._children = []  # type: List[Activity]
        self._volatile_children = []  # type: List[Activity]
        self._done = Flag()
        self._activity = None

    def __await__(self):
        yield from self._done.__await__()

    def do(self, payload: Coroutine[Any, Any, RT], *, after: float = None, at: float = None, volatile: bool = False) -> Activity[RT]:
        """
        Concurrently perform an activity in this scope

        :param payload: the activity to perform
        :param after: delay after which to start the activity
        :param at: point in time at which to start the activity
        :param volatile: whether the activity is aborted at the end of the scope
        :return: representation of the ongoing activity

        All non-`volatile` activities are `await`\ ed at the end of the scope.
        As a result, the scope only ends after all its child activities are done.
        If an activity needs to shut down gracefully with its scope,
        it can `await` the scope.

        .. code:: python

            async def graceful(containing_scope: Scope):
                print('waiting for end of scope ...')
                await containing_scope
                print('... scope has finished')

            with Scope() as scope:
                scope.do(graceful(scope))

        All `volatile` activities are aborted at the end of the scope,
        after all non-`volatile` activities have finished.
        Aborting ``volatile` activities is not graceful:
        :py:class:`GeneratorExit` is raised in the activity,
        and must exit without `await`\ ing or `yield`\ ing anything.
        """
        if after is not None and at is not None:
            raise ValueError("only one of 'after' and 'at' can be used at once")
        child_activity = Activity(payload)
        __LOOP_STATE__.LOOP.schedule(
            child_activity.__runner__(),
            delay=after, at=at
        )
        if not volatile:
            self._children.append(child_activity)
        else:
            self._volatile_children.append(child_activity)
        return child_activity

    async def _await_children(self):
        for child in self._children:
            await child

    async def _cancel_children(self):
        for child in self._children:
            child.cancel(self)

    async def _close_volatile(self):
        for child in self._volatile_children:
            child.__close__()

    async def __aenter__(self):
        if self._activity is not None:
            raise RuntimeError('%r is not re-entrant' % self.__class__.__name__)
        self._activity = __LOOP_STATE__.LOOP.activity
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is GeneratorExit:
            for child in self._children + self._volatile_children:
                child.__close__()
            return False
        assert self._activity is __LOOP_STATE__.LOOP.activity,\
            "Instances of %s cannot be shared between activities" % self.__class__.__name__
        await self._done.set()
        await self._await_children()
        await self._close_volatile()
        return False


class InterruptScope(Scope):
    """
    Scope that is closed on notification

    :see: :py:func:`~.until`
    """
    __slots__ = ('_notification', '_interrupt')

    def __init__(self, notification: Notification):
        super().__init__()
        self._notification = notification
        self._interrupt = CoreInterrupt(notification, id(self))

    async def __aenter__(self):
        await super().__aenter__()
        self._notification.__subscribe__(self._activity, self._interrupt)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # there was no exception, we simply reached end of scope
        # wait for children to die by themselves
        if exc_type is None:
            try:
                await super().__aexit__(exc_type, exc_val, exc_tb)
            except BaseException as err:
                exc_type, exc_val = type(err), err
            else:
                self._notification.__unsubscribe__(self._activity, self._interrupt)
                return True
        # GeneratorExit might have been thrown in super().__aexit__ as well
        if exc_type is GeneratorExit:
            for child in self._children + self._volatile_children:
                child.__close__()
            return False
        # there was an exception, we have to abandon the scope
        # reap all children now
        await self._cancel_children()
        if exc_val is self._interrupt:
            await super().__aexit__(exc_type, exc_val, exc_tb)
            return True
        self._notification.__unsubscribe__(self._activity, self._interrupt)
        await super().__aexit__(exc_type, exc_val, exc_tb)
        return False

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._notification)


def until(notification: Notification):
    """
    :py:class:`Scope` that is interrupted on notification

    An asynchronous `until`-scope listens for a notification *without* stopping execution.
    This allows notification on any break point, i.e. `await` in the context or while waiting for children.

    .. code:: python

        async with until(done):
            await eternity  # infinite waiting, interrupted by notification

        async with until(done) as scope:
            scope.do(eternity)  # infinite activity, interrupted by notification

    :note: A break point in the context is always required,
           even when the notification would trigger immediately.
    """
    return InterruptScope(notification)
