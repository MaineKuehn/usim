r"""
event handling core facilities

This is the core scheduling/synchronization implementation.
It defines a basic event loop with simulated time, as well as the signals
understood by the loop.
The entirety of this module is for internal use only, and should not be used
by simulation code directly.
"""
import collections
import threading
from typing import Coroutine, TypeVar, Optional, Union, Generator

from .waitq import WaitQueue


# Errors
class ActivityError(RuntimeError):
    r"""An activity failed to handle an exception"""
    def __init__(self, activity: Coroutine, signal: Optional[BaseException]):
        self.activity = activity
        self.signal = signal
        super().__init__(
            'Activity %r raised an exception in response to %s' % (
                activity, signal
            )
        )


class ActivityLeak(RuntimeError):
    r"""An activity failed to contain output"""
    def __init__(self, activity: Coroutine, signal: Optional[BaseException], result):
        self.activity = activity
        self.signal = signal
        self.result = result
        super().__init__(
            'Activity %r returned %r in response to %s' % (
                activity, result, signal
            )
        )


# Coroutine Return Type
RT = TypeVar('RT')


class MissingLoop:
    r"""
    Placeholder for the :py:class:`~.Loop` expected in an active simulation

    This class exists to provide helpful error messages if usim is used
    without starting its event loop. If you encounter this class unexpectedly,
    see 'https://usim.readthedocs.io' for details.
    """
    __slots__ = ('_entry_point',)

    def __init__(self, entry_point: str = 'usim.run'):
        self._entry_point = entry_point

    def __getattr__(self, field: str):
        raise RuntimeError((
            "field '%s' can only be accessed with an active usim event loop\n\n"
            "You have attempted to use an async feature of usim outside of\n"
            "a usim simulation. This likely means that you used a different\n"
            "async framework. You must run usim's async features as part of\n"
            "an active usim simulation.\n\n"
            "Use '%s' to start an appropriate simulation."
        ) % (field, self._entry_point))

    def __repr__(self):
        return '{self.__class__.__name__}(entry_point={self._entry_point})'.format(
            self=self,
        )


__LOOP_STATE__ = threading.local()
__LOOP_STATE__.LOOP = MissingLoop()  # type: Union[MissingLoop, Loop]


# Commands
class Hibernate(object):
    r"""
    Pause current execution indefinitely

    When yielding this event to :py:class:`~.Loop`,
    the current activity is suspended.
    It can be used both in asynchronous functions
    and synchronous generators;
    the latter is intended for ``__await__`` methods.

    This class is stateless and effectively works like a singleton.
    Use :py:attr:`~.__HIBERNATE__` to avoid creating new instances.

    .. code:: python3

        async def sleep():
            await __HIBERNATE__

        class Sleep:
            def __await__():
                yield from __HIBERNATE__
    """
    __slots__ = ()

    def __await__(self) -> 'Generator[Hibernate, None, None]':
        yield self

    __iter__ = __await__


#: reusable instance of :py:class:`Hibernate`
__HIBERNATE__ = Hibernate()


class Loop:
    r"""
    Interrupt based event loop with side-channel control using simulated time

    :param coroutines: the initial payloads to run
    :param start: the initial time of the simulation
    :ivar time: the current simulation time
    :ivar turn: the number of coroutines run in the current time step so far
    :ivar activity: the coroutine currently executing

    The event loop runs a number of coroutines concurrently.
    By interacting with the event loop to exchange commands,
    coroutines are synchronized.
    Commands are either ``await``\ able, issued in an ``async def`` coroutine,
    or side-channel via ``__LOOP_STATE__.LOOP``,
    issued by either coroutines or subroutines.

    The event loop understands only a single ``await``\ able command,
    :py:class:`Hibernate`, which immediately suspends the currently active coroutine.
    This does *not* schedule the coroutine for resumption.
    This must be done separately.

    .. code:: python

        async def sleep():
            print('start')
            await Hibernate()  # suspend execution indefinitely
            print('awoken')    # only run if the coroutine is re-scheduled somehow

    The :py:class:`Loop` instance running in the current thread
    is available as ``__LOOP_STATE__.LOOP``.
    This reference may be used by coroutines to send non-suspending commands
    to the loop.

    The event loop understands only a single side-channel command,
    :py:meth:`~.Loop.schedule`, which schedules the execution of a coroutine
    at a simulated time point.
    A coroutine is executed either by sending :py:const:`None`
    or throwing an :py:class:`~.Interrupt`.

    .. code:: python

        async def sleep(duration: float):
            print('start')
            interrupt = Interrupt('sleep', duration)
            # awake current activity from sleep via a scheduled interrupt
            __LOOP_STATE__.LOOP.schedule(__LOOP_STATE__.LOOP.activity, delay=duration)
            try:
                await Hibernate()
            finally:
                # revoke the interrupt on exit in case *another* interrupt occured
                interrupt.revoke()

    Sending :py:const:`None` must be used for the first schedule,
    while :py:class:`~.Interrupt` should be used for subsequent ones.
    Note that only :py:class:`~.Interrupt` can be revoked.
    The :py:class:`Loop` can also handle subclasses of :py:class:`~.Interrupt`,
    allowing to efficiently send interrupts with payloads.
    """
    __slots__ = ('time', 'turn', 'activity', '_annotations', '_activations', '_pending')

    def __init__(self, *coroutines: Coroutine, start: float = 0):
        self.time = start
        self.turn = 0
        self._activations = WaitQueue()  # type: WaitQueue[float, Activation]
        self.activity = None  # type: Coroutine
        for coroutine in coroutines:
            self._activations.push(self.time, Activation(coroutine))
        self._pending = None  # type: collections.deque[Activation]

    def __repr__(self):
        return '<%s @ %s:%s, %d pending, %d queued>' % (
            self.__class__.__name__,
            self.time,
            self.turn,
            len(self._pending),
            len(self._activations),
        )

    def run(self):
        r"""Run the event loop in the current thread"""
        outer_loop = __LOOP_STATE__.LOOP
        __LOOP_STATE__.LOOP = self
        try:
            self._run_events()
        finally:
            __LOOP_STATE__.LOOP = outer_loop

    def _run_events(self):
        r"""event loop core, processing all scheduled coroutines"""
        activations = self._activations
        while activations:
            now, pending = activations.pop()
            self.time = now
            self.turn = 0
            self._pending = pending
            while pending:
                activation = pending.popleft()
                if activation:
                    self.turn += 1
                    self.activity = activation.target
                    self._run_coroutine(activation.target, activation.signal)
                    self.activity = None

    def _run_coroutine(self, target: Coroutine, signal: BaseException = None):
        r"""event loop kernel, processing a single coroutine"""
        try:
            if signal is not None:
                reply = target.throw(signal)
            else:
                reply = target.send(None)
            assert (
                type(reply) is Hibernate
            ), '%s received %s but only supports the Hibernate command' % (
                self.__class__.__name__, reply
            )
        except StopIteration as err:
            if err.args:
                # async def ... return foo -> StopIteration.args == (foo,)
                raise ActivityLeak(target, signal, err.args[0]) from err
        except BaseException as err:
            raise ActivityError(target, signal=signal) from err

    def schedule(
            self,
            target: Coroutine,
            signal: 'Interrupt' = None, *,
            delay: float = None,
            at: float = None
    ):
        r"""
        Schedule the execution of a coroutine

        :param target: the coroutine to execute
        :param signal: exception to `.throw` into the coroutine
        :param delay: relative delay until executing the coroutine
        :param at: absolute delay until executing the coroutine

        Coroutines are executed using `target.send(None)` unless `signal` is provided,
        in which case `target.throw(signal)` is used instead.
        """
        assert (
            delay is None or at is None
        ), "schedule date must be either absolute or relative"
        if delay is None and at is None:
            self._pending.append(Activation(target, signal))
        elif delay is not None:
            assert delay > 0, "schedule date must not be in the past"
            self._activations.push(self.time + delay, Activation(target, signal))
        elif at is not None:
            assert at > self.time, "schedule date must not be in the past"
            self._activations.push(at, Activation(target, signal))
        if signal is not None:
            signal.scheduled = True


class Interrupt(BaseException):
    r"""Internal Interrupt signal for operations"""
    __slots__ = ('token', 'scheduled', '_revoked')

    def __init__(self, *token):
        self.token = token
        self.scheduled = False
        self._revoked = False
        BaseException.__init__(self, token)

    def __bool__(self):
        return not self._revoked

    def revoke(self):
        r"""Revoke the interrupt, cancelling any pending activation with it"""
        self._revoked = True

    def __repr__(self):
        return "<{}.{} token{} @{}: {}>".format(
            self.__class__.__module__, self.__class__.__qualname__,
            ' (revoked)' if self._revoked else '',
            id(self),
            ', '.join(repr(item) for item in self.token),
        )


class Activation(object):
    r"""Scheduled activation of a coroutine with a given signal"""
    __slots__ = ('target', 'signal')

    def __init__(self, target: Coroutine, signal: Interrupt = None):
        self.target = target
        self.signal = signal

    def __bool__(self) -> bool:
        return self.signal is None or not self.signal._revoked

    def __repr__(self):
        return '<%s of %s%s%s>' % (
            self.__class__.__name__,
            self.target,
            '' if self.signal is None else ' via %s' % self.signal,
            '' if self else ' (cancelled)'
        )
