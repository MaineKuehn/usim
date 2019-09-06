from typing import Coroutine, List, TypeVar, Any, Optional, Tuple

from .._core.loop import __LOOP_STATE__, Interrupt as CoreInterrupt
from .notification import Notification
from .flag import Flag
from .task import Task, TaskClosed, TaskState, TaskCancelled
from .concurrent_exception import Concurrent


RT = TypeVar('RT')


class VolatileTaskClosed(TaskClosed):
    """A volatile :py:class:`~.Task` forcefully exited at the end of its scope"""


class CancelScope(CoreInterrupt):
    """A :py:class:`Scope` is being cancelled"""
    __slots__ = ('subject',)

    def __init__(self, subject: 'Scope', *token):
        super().__init__(*token)
        self.subject = subject


class Scope:
    r"""
    Concurrency scope that allows branching off and waiting for multiple activities

    A new :py:class:`~.Scope` must be opened in an ``async with`` block.
    During its block, a :py:class:`~.Scope` may :py:meth:`~.Scope.do`
    several activities concurrently.
    The :py:class:`~.Scope` owns and supervises all branched off activities.

    .. code:: python3

        async def show_clock(interval=1):
            "An infinite loop showing the current time"
            async for now in every(interval=interval):
                print(now)

        async with Scope() as scope:
            scope.do(time + 20)  # scope can launch multiple activities at once...
            scope.do(time + 20)
            scope.do(time + 20)
            scope.do(
                show_clock(),
                volatile=True
            )  #  ...and mark some as expendable on exit
            # block is exited once the three delays finished concurrently
        # block is done after a total delay of 20

    Both the block of scope and all its activities form one unit of control.
    A :py:class:`~.Scope` will only exit once its block and all non-``volatile``
    activities are done.
    If either encounters an unhandled exception, all are aborted;
    exceptions from child tasks are collapsed into a single :py:exc:`~.Concurrent`
    exception which is raised by the :py:class:`~.Scope`.
    Only the fatal exception types :py:exc:`SystemExit`, :py:exc:`KeyboardInterrupt`,
    and :py:exc:`AssertionError` are not collapsed, but propagated directly.

    During its lifetime, a :py:class:`~.Scope` can be passed around freely.
    Most importantly, it can be passed to child activities.
    This allows to :py:meth:`~.Scope.do` things in a parent scope, and to ``await``
    the end of the scope.

    .. code:: python3

        def do_some(scope):
            "Perform several actions in a parent scope"
            for delay in range(0, 20, 5):
                scope.do(time + delay)

        async def on_done(scope):
            "Wait for a scope to end and report it"
            await scope
            print('Scope is done at', time.now)

        async with Scope() as scope:
            do_some(scope)  # pass scope around to do activities in it
            on_done(scope)  # pass scope around to await its end
    """
    __slots__ = '_children', '_body_done', '_activity', '_volatile_children',\
                '_cancel_self', '_interruptable'

    #: Exceptions which are *not* re-raised from concurrent tasks
    SUPPRESS_CONCURRENT = (
        TaskCancelled, TaskClosed, GeneratorExit
    )
    #: Exceptions which are always propagated unwrapped
    PROMOTE_CONCURRENT = (
        SystemExit, KeyboardInterrupt, AssertionError
    )

    def __init__(self):
        self._children = []  # type: List[Task]
        self._volatile_children = []  # type: List[Task]
        # the scope body is finished and we do/did __aexit__
        self._body_done = Flag()
        # we can still be cancelled/interrupted asynchronously
        self._interruptable = True
        self._activity = None  # type: Optional[Coroutine]
        self._cancel_self = CancelScope(self, 'Scope._cancel_self')

    def __await__(self):
        yield from self._body_done.__await__()

    def do(
            self,
            payload: Coroutine[Any, Any, RT],
            *,
            after: float = None,
            at: float = None,
            volatile: bool = False
    ) -> Task[RT]:
        r"""
        Concurrently perform an activity in this scope

        :param payload: the activity to perform
        :param after: delay after which to start the activity
        :param at: point in time at which to start the activity
        :param volatile: whether the activity is aborted at the end of the scope
        :return: representation of the ongoing activity

        All non-``volatile`` activities are ``await``\ ed at the end of the scope.
        As a result, the scope only ends after all its child activities are done.
        Unhandled exceptions in children cause the parent scope to abort immediately;
        all child exceptions are collected and re-raised as part of a single
        :py:exc:`~.Concurrent` exception in this case.

        If an activity needs to shut down gracefully with its scope,
        it can `await` the scope.

        .. code:: python

            async def graceful(containing_scope: Scope):
                print('waiting for end of scope ...')
                await containing_scope
                print('... scope has finished')

            async with Scope() as scope:
                scope.do(graceful(scope))

        All ``volatile`` activities are aborted at the end of the scope,
        after all non-``volatile`` activities have finished.
        Aborting ``volatile`` activities is not graceful:
        :py:class:`GeneratorExit` is raised in the activity,
        which must exit without ``await``\ ing or ``yield``\ ing anything.
        """
        assert after is None or at is None,\
            "schedule date must be either absolute or relative"
        assert after is None or after > 0,\
            "schedule date must not be in the past"
        assert at is None or at > __LOOP_STATE__.LOOP.time,\
            "schedule date must not be in the past"
        child_task = Task(payload, self, delay=after, at=at)
        __LOOP_STATE__.LOOP.schedule(
            child_task.__runner__,
        )
        if not volatile:
            self._children.append(child_task)
        else:
            self._volatile_children.append(child_task)
        return child_task

    def __cancel__(self):
        """Cancel this scope"""
        if self._interruptable:
            __LOOP_STATE__.LOOP.schedule(self._activity, self._cancel_self)

    def _disable_interrupts(self):
        self._interruptable = False
        self._cancel_self.revoke()

    async def _await_children(self):
        for child in self._children:
            await child.done

    def _close_children(self):
        """Forcefully close all child non-volatile tasks"""
        reason = TaskClosed("closed at end of scope '%s'" % self)
        for child in self._children:
            child.__close__(reason=reason)

    def _close_volatile(self):
        """Forcefully close all volatile child tasks"""
        reason = VolatileTaskClosed("closed at end of scope '%s'" % self)
        for child in self._volatile_children:
            child.__close__(reason=reason)

    async def __aenter__(self):
        if self._activity is not None:
            raise RuntimeError('%r is not re-entrant' % self.__class__.__name__)
        self._activity = __LOOP_STATE__.LOOP.activity
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            try:
                # inform everyone that we are shutting down
                # we may receive any shutdown signal here
                await self._body_done.set()
            except BaseException as err:
                exc_type, exc_val = type(err), err
            else:
                return await self._aexit_graceful()
        self._body_done._value = True
        self._body_done.__trigger__()
        # there was an exception, we have to abandon the scope
        return self._aexit_forceful(exc_type, exc_val)

    def _aexit_forceful(self, exc_type, exc_val) -> bool:
        """
        Exit with exception

        This immediately closes all children without waiting for anything.
        No further interrupts can occur during shutdown (this is a sync function).

        If a fatal exception occurred in this scope or a child, the fatal
        exception replaces all other exceptions in flight.
        If the current exception is suppressed by the scope, any exceptions from
        children are reraised as :py:exc:`~.Concurrent` errors.
        """
        # we already handle an exception, suppress
        self._disable_interrupts()
        # reap all children now
        self._close_children()
        self._close_volatile()
        return self._propagate_exceptions(exc_type, exc_val)

    async def _aexit_graceful(self) -> bool:
        """
        Exit without exception

        This suspends the scope until all children have finished themselves.
        If any children encountered an error, they are reraised as
        :py:exc:`~.Concurrent` errors.

        If an error occurs while waiting for children to stop, a forceful
        shutdown is performed instead.
        """
        try:
            await self._await_children()
        except BaseException as err:
            return self._aexit_forceful(type(err), err)
        else:
            # everybody is gone - we just handle the cleanup
            self._disable_interrupts()
            self._close_volatile()
            return self._propagate_exceptions(None, None)

    def _collect_exceptions(self)\
            -> Tuple[Optional[BaseException], Optional[Concurrent]]:
        """
        collect any privileged and concurrent exceptions that occurred in children

        This returns a tuple ``(privileged, concurrent)`` of which both may be
        :py:const:`None` if no appropriate exception is found.
        """
        suppress = self.SUPPRESS_CONCURRENT
        promote = self.PROMOTE_CONCURRENT
        concurrent = []
        for child in self._children:
            if child.status is TaskState.FAILED:
                exc = child.__exception__
                if isinstance(exc, promote):
                    return exc, None
                if not isinstance(exc, suppress):
                    concurrent.append(exc)
        if concurrent:
            return None, Concurrent(*concurrent)
        return None, None

    def _propagate_exceptions(self, exc_type, exc_val):
        if exc_type in self.PROMOTE_CONCURRENT:
            # we already have a privileged exception, there is nothing more important
            # propagate it
            return False
        elif self._is_suppressed(exc_val):
            # we do not have an exception to propagate, take whatever we can get
            privileged, concurrent = self._collect_exceptions()
            if privileged is not None or concurrent is not None:
                raise privileged or concurrent
            # we handled our own and there was nothing else to propagate
            return True
        else:
            # we already have an exception to propagate, take only important ones
            privileged, _ = self._collect_exceptions()
            if privileged is not None:
                raise privileged
            # we still have our unhandled exception to propagate
            return False

    def _is_suppressed(self, exc_val) -> bool:
        """
        Whether the exception is handled completely by :py:meth:`~.__aexit__`

        This generally means that the exception was an interrupt for this scope.
        If the exception is meant for anyone else, we should let it propagate.
        """
        return exc_val is self._cancel_self

    def __repr__(self):
        return (
            '<{self.__class__.__name__}, children={children}, volatile={volatile}'
            ', done={done}'
            ' @ {address}>'
        ).format(
            self=self,
            done=bool(self._body_done),
            children=len(self._children),
            volatile=len(self._volatile_children),
            address=id(self),
        )


class InterruptScope(Scope):
    r"""
    Scope that is closed on notification

    :see: :py:func:`~.until`
    """
    __slots__ = ('_notification', '_interrupt')

    def __init__(self, notification: Notification):
        super().__init__()
        self._notification = notification
        self._interrupt = CancelScope(self, notification)

    async def __aenter__(self):
        await super().__aenter__()
        self._notification.__subscribe__(self._activity, self._interrupt)
        return self

    def _disable_interrupts(self):
        self._notification.__unsubscribe__(self._activity, self._interrupt)
        super()._disable_interrupts()

    def _is_suppressed(self, exc_val) -> bool:
        return exc_val is self._interrupt or super()._is_suppressed(exc_val)

    def __repr__(self):
        return (
            '<{self.__class__.__name__}, children={children}, volatile={volatile}'
            ', done={done}'
            ', notification={self._notification}'
            ' @ {address}>'
        ).format(
            self=self,
            done=bool(self._body_done),
            children=len(self._children),
            volatile=len(self._volatile_children),
            address=id(self),
        )


def until(notification: Notification):
    r"""
    :py:class:`Scope` that is interrupted on notification

    An asynchronous `until`-scope listens for a notification
    *without* stopping execution.
    This allows notification on any break point,
    e.g. `await` in the context or while waiting for children.

    .. code:: python

        async with until(done):
            await eternity  # infinite waiting, interrupted by notification

        async with until(done) as scope:
            scope.do(eternity)  # infinite activity, interrupted by notification

    :note: A break point in the context is always required,
           even when the notification would trigger immediately.
    """
    return InterruptScope(notification)
