import collections
from typing import Coroutine, Tuple, List, TypeVar, Awaitable

from .waitq import WaitQueue


# Coroutine Return Type
RT = TypeVar('RT')
# The latest point in time we can wait for
INFINITY = float('inf')


def run(*coroutines: Coroutine, start: float = 0):
    interrupt_queue = WaitQueue()
    for coroutine in coroutines:
        interrupt_queue.push(start, Activation(coroutine, deadline=start))
    while interrupt_queue:
        now, current_interrupts = interrupt_queue.pop()
        current_interrupts = collections.deque(current_interrupts)
        while current_interrupts:
            interrupt = current_interrupts.popleft()  # type: Activation
            if interrupt:
                delayed, immediate = run_step(interrupt.target, now, interrupt.signal)
                interrupt_queue.update(delayed)
                current_interrupts.extend(immediate)


def run_step(target: Coroutine, now, signal=None):
    """Advance coroutine for the current time step"""
    enqueue = []  # type: List[Tuple[float, Activation]]
    resume = []  # type: List[Activation]
    message = None
    try:
        while True:
            if signal is not None:
                command = target.throw(signal)
                signal = None
            else:
                command = target.send(message)
            if isinstance(command, Schedule):
                if command.delay > 0:
                    message = Activation(command.target, now + command.delay, command.signal)
                    enqueue.append((message.deadline, message))
                else:
                    message = Activation(command.target, now, command.signal)
                    resume.append(message)
            elif isinstance(command, GetTime):
                message = now
            elif isinstance(command, GetTask):
                message = target
            elif isinstance(command, Hibernate):
                break
            else:
                # send the error to the coroutine
                #  - if it was an error, we get a traceback
                #  - if it was a probe, it can catch the error
                signal = RuntimeError('result %r is not a %s command' % (command, target.__class__.__name__))
    except StopIteration as err:
        assert not err.args, 'coroutine %s returned output without a caller to receive it' % target
    return enqueue, resume


class Interrupt(Exception):
    """Internal Interrupt signal for operations"""
    def __init__(self, *token):
        self.token = token
        self.scheduled = False
        self._revoked = False
        Exception.__init__(self, token)

    def __bool__(self):
        return not self._revoked

    def revoke(self):
        self._revoked = True

    def __repr__(self):
        return "<{}.{} token{} @{}: {}>".format(
            self.__class__.__module__, self.__class__.__qualname__,
            ' (revoked)' if self._revoked else '',
            id(self),
            ', '.join(repr(item) for item in self.token),
        )

    __str__ = __repr__


class Activation(object):
    def __init__(self, target: Coroutine, deadline: float, signal: Interrupt = None):
        self.target = target
        self.deadline = deadline
        self.signal = signal
        if signal is not None:
            signal.scheduled = True

    def __bool__(self) -> bool:
        return self.signal is None or bool(self.signal)

    def __repr__(self):
        return '<%s of %s at %s%s%s>' % (
            self.__class__.__name__,
            self.target,
            self.deadline,
            '' if self.signal is None else ' via %s' % self.signal,
            '' if self else ' (cancelled)'
        )


# Commands
class Hibernate(object):
    """Pause current execution indefinitely"""
    def __await__(self):
        return (yield self)


class Schedule(object):
    """Schedule the activation of a coroutine"""
    def __init__(self, target: Coroutine, delay: float = 0, signal: BaseException = None):
        self.target = target
        self.signal = signal
        self.delay = delay

    def __await__(self) -> Awaitable[Activation]:
        return (yield self)


class GetTime(object):
    """Get the current time"""
    def __await__(self) -> Awaitable[float]:
        return (yield self)


class GetTask(object):
    """Get the current Task"""
    def __await__(self) -> Awaitable[Coroutine]:
        return (yield self)
