from functools import wraps
import enum
from typing import Coroutine, TypeVar, Awaitable, Optional, Tuple, Any, List,\
    TYPE_CHECKING

from .._core.loop import __LOOP_STATE__, Interrupt
from .notification import suspend
from .condition import Condition
if TYPE_CHECKING:
    from .context import Scope


RT = TypeVar('RT')


def try_close(coroutine: Coroutine):
    """Attempt to close a coroutine-like object if possible"""
    try:
        close = coroutine.close
    except AttributeError:
        pass
    else:
        close()


# enum.Flag is Py3.6+
class TaskState(enum.Flag if hasattr(enum, 'Flag') else enum.IntEnum):
    """State of a :py:class:`~.Task`"""
    #: created but not running yet
    CREATED = 2 ** 0
    #: being executed at the moment
    RUNNING = 2 ** 1
    #: finished due to cancellation
    CANCELLED = 2 ** 2
    #: finished due to an unhandled exception
    FAILED = 2 ** 3
    #: finished normally
    SUCCESS = 2 ** 4
    #: finished by any means
    FINISHED = CANCELLED | FAILED | SUCCESS


class TaskCancelled(Exception):
    """A :py:class:`~.Task` has been cancelled"""
    __slots__ = ('subject',)

    def __init__(self, subject: 'Task', *token):
        super().__init__(*token)
        #: the cancelled Task
        self.subject = subject


class CancelTask(Interrupt):
    """A :py:class:`~.Task` is being cancelled"""
    __slots__ = ('subject',)

    def __init__(self, subject: 'Task', *token):
        super().__init__(*token)
        #: the Task being cancelled
        self.subject = subject

    @property
    def __transcript__(self) -> TaskCancelled:
        result = TaskCancelled(self.subject, *self.token)
        result.__cause__ = self
        return result


class TaskClosed(Exception):
    """A :py:class:`~.Task` forcefully exited"""


class Task(Awaitable[RT]):
    """
    Concurrently running activity

    A :py:class:`Task` wraps a ``payload`` :term:`activity` that is
    concurrently run in a ``parent`` :py:class:`~.Scope`.
    This allows to store or pass on the :py:class:`Task`
    in order to control the underlying activity.
    Other activities can ``await`` a :py:class:`Task`
    to receive results or exceptions on completion,
    similar to a regular activity.

    .. code:: python3

        async def my_activity(delay):
            await (time + delay)
            return delay

        await my_activity()  # await an activity

        async with Scope() as scope:
            task = scope.do(my_activity())
            await task   # await Task of an activity

    In contrast to a bare activity, it is possible to

    * :py:meth:`~.Task.cancel` a :py:class:`Task` before completion,
    * ``await`` the result of a :py:class:`Task` multiple times,
      and
    * ``await`` that a :py:class:`Task` is :py:attr:`~.Task.done`.

    :note: This class should not be instantiated directly.
           Always use a :py:class:`~.Scope` to create it.
    """
    __slots__ = 'payload', '_result', '__runner__', '_cancellations', '_done', 'parent'

    def __init__(self, payload: Coroutine[Any, Any, RT], parent: 'Scope', delay, at):
        @wraps(payload)
        async def payload_wrapper():
            # check for a pre-run cancellation
            if self._result is not None:
                try_close(self.payload)
                return
            try:
                # We suspend the Task internally instead of waiting to start
                # the Task externally. This is because starting must *always*
                # be done via ``Task.__runner__.send(None)`` which we *cannot*
                # cancel cleanly. An internal suspension means we *can* cancel
                # the Task pre-run because no time passes until we check that.
                if delay or at:
                    await suspend(delay=delay, until=at)
                result = await self.payload
            except CancelTask as err:
                assert (
                    err.subject is self
                ), "task for activity %r received cancellation of %r" % (
                    self, err.subject
                )
                self._result = None, err.__transcript__
            except GeneratorExit:
                # We are NOT allowed to do any async once the generator
                # exits forcefully.
                # We should only receive GeneratorExit due to a forceful
                # termination in self.__close__ or during cleanup.
                pass
            except BaseException as err:
                self._result = None, err
                self.parent.__cancel__()
            else:
                self._result = result, None
            for cancellation in self._cancellations:
                cancellation.revoke()
            try_close(self.payload)
            self._done.__set_done__()
        self._cancellations = []  # type: List[CancelTask]
        self._result = None  \
            # type: Optional[Tuple[Optional[RT], Optional[BaseException]]]
        self.payload = payload
        self.parent = parent
        self._done = Done(self)
        self.__runner__ = payload_wrapper()  # type: Coroutine[Any, Any, RT]

    def __await__(self):
        yield from self._done.__await__()
        result, error = self._result
        if error is not None:
            raise error
        else:
            return result  # noqa: B901

    @property
    def __exception__(self) -> Optional[BaseException]:
        """Get the exception of this task"""
        assert self._result is not None,\
            f'Task.__exception__ may only be queried for finished tasks'
        return self._result[1]

    @property
    def done(self) -> 'Done':
        """
        :py:class:`~.Condition` whether the :py:class:`~.Task` has stopped running.
        This includes completion, cancellation and failure.
        """
        return self._done

    @property
    def status(self) -> TaskState:
        """The current status of this activity"""
        if self._result is not None:
            result, error = self._result
            if error is not None:
                return (
                    TaskState.CANCELLED
                    if isinstance(error, (TaskCancelled, TaskClosed))
                    else TaskState.FAILED
                )
            return TaskState.SUCCESS
        # a stripped-down version of `inspect.getcoroutinestate`
        if self.__runner__.cr_frame.f_lasti == -1:
            return TaskState.CREATED
        return TaskState.RUNNING

    def __close__(self, reason=TaskClosed('activity closed')):
        """
        Close the underlying coroutine

        This is similar to calling :py:meth:`Coroutine.close`,
        but ensures that waiting activities are properly notified.
        """
        # we have not FINISHED running yet, and can still change the result
        if self._result is None:
            self._result = None, reason
            if self.__runner__.cr_frame.f_lasti == -1:
                # We have not STARTED running yet
                # This means __runner__ will start running in the same time frame.
                # We cannot .close() it, since it must receive the un-cancellable
                # initial .send(None).
                # We prepare the state *as if* we had stopped; the __runner__
                # will then shutdown at a later turn without observable side-effects.
                self._done.__set_done__()
            else:
                # We are RUNNING and __runner__ is prepared to catch GeneratorExit
                # Close the __runner__ to have it clean up and finalize everything.
                self.__runner__.close()

    def cancel(self, *token) -> None:
        """
        Cancel this task during the current time step

        If the :py:class:`~.Task` is running,
        a :py:class:`~.CancelTask` is raised once the activity suspends.
        The activity may catch and react to :py:class:`~.CancelActivity`,
        but should not suppress it.

        If the :py:class:`~.Task` is :py:attr:`~.Task.done` before
        :py:class:`~.CancelTask` is raised, the cancellation is ignored.
        This also means that cancelling an activity multiple times is allowed,
        but only the first successful cancellation is stored as the cancellation cause.

        If the :py:class:`~.Task` has not started running, it is cancelled immediately.
        This prevents any code execution, even before the first suspension.

        :warning: The timing of cancelling a Task before it started running
                  may change in the future.
        """
        if self._result is None:
            if self.status is TaskState.CREATED:
                self._result = None, TaskCancelled(self, *token)
                self._done.__set_done__()
            else:
                cancellation = CancelTask(self, *token)
                self._cancellations.append(cancellation)
                cancellation.scheduled = True
                __LOOP_STATE__.LOOP.schedule(self.__runner__, signal=cancellation)

    def __repr__(self):
        return '<%s of %s (%s)>' % (
            self.__class__.__name__, self.payload,
            'outstanding' if self._result is None else (
                'result={!r}'.format(self._result[0])
                if self._result[1] is None
                else
                'signal={!r}'.format(self._result[1])
            ),
        )

    def __del__(self):
        # Since a Task is only meant for use in a controlled
        # fashion, going out of scope unexpectedly means there is
        # a bug/error somewhere. This should be accompanied by an
        # error message or traceback.
        # In order not to detract with auxiliary, useless resource
        # warnings, we clean up silently to hide our abstraction.
        self.__runner__.close()


class Done(Condition):
    """Whether a :py:class:`Task` has stopped running"""
    __slots__ = ('_task', '_value', '_inverse')

    def __init__(self, task: Task):
        super().__init__()
        self._task = task
        self._value = False
        self._inverse = NotDone(self)

    def __bool__(self):
        return self._value

    def __invert__(self):
        return self._inverse

    def __set_done__(self):
        """Set the boolean value of this condition"""
        assert not self._value
        self._value = True
        self.__trigger__()

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, self._task)


class NotDone(Condition):
    """Whether a :py:class:`Task` has not stopped running"""
    __slots__ = ('_done',)

    def __init__(self, done: Done):
        super().__init__()
        self._done = done

    def __bool__(self):
        return not self._done

    def __invert__(self):
        return self._done

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, self._done._task)
