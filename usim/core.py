import collections
from typing import Coroutine, Tuple, Any, List, TypeVar, Awaitable

from .waitq import WaitQueue
from .utility import name
from .multi_error import MultiError


# Coroutine Return Type
RT = TypeVar('RT')
# The latest point in time we can wait for
INFINITY = float('inf')


def run(*coroutines: Coroutine, start: float = 0):
    now = start
    interrupt_queue = WaitQueue()
    tasks = [Task(coroutine) for coroutine in coroutines]
    for task in tasks:
        interrupt_queue.push(now, Resumption(task, deadline=now))
    while interrupt_queue:
        now, current_interrupts = interrupt_queue.pop()
        current_interrupts = collections.deque(current_interrupts)
        while current_interrupts:
            interrupt = current_interrupts.popleft()  # type: Resumption
            if interrupt:
                delayed, immediate = interrupt.target.resume(now, interrupt.signal)
                current_interrupts.extend(immediate)
                interrupt_queue.update(delayed)
    return collect(*tasks)


class Task(object):
    def __init__(self, coroutine: Coroutine[Any, Any, RT]):
        self.coroutine = coroutine
        self._done = False
        self._waiters = []  # type: List[Task]
        self._result = None  # type: Tuple[Any, Exception]

    @property
    def result(self):
        if not self._done:
            raise RuntimeError('%s did not complete')
        result, error = self._result
        if error is not None:
            raise error
        else:
            return result

    def resume(self, now, signal=None):
        """Advance coroutine for the current time step"""
        enqueue = []  # type: List[Tuple[float, Resumption]]
        resume = []  # type: List[Resumption]
        coroutine, message = self.coroutine, None
        try:
            while True:
                if signal is not None:
                    command = coroutine.throw(signal)
                    signal = None
                else:
                    command = coroutine.send(message)
                if isinstance(command, Schedule):
                    if command.delay > 0:
                        message = Resumption(
                            command.target if command.target is not None else self, now + command.delay, command.signal
                        )
                        enqueue.append((message.deadline, message))
                    else:
                        message = Resumption(
                            command.target if command.target is not None else self, now, command.signal
                        )
                        resume.append(message)
                elif isinstance(command, GetTime):
                    message = now
                elif isinstance(command, GetTask):
                    message = self
                elif isinstance(command, Hibernate):
                    break
                else:
                    raise ValueError('result %r is not an %s command' % (command, self.__class__.__name__))
        except Exception as exit_signal:
            resume.extend([Resumption(task, now) for task in self._waiters])
            self._complete(exit_signal)
        return enqueue, resume

    def _complete(self, signal):
        self._done = True
        if isinstance(signal, StopIteration):
            self._result = signal.value, None
        else:
            self._result = None, signal

    def __await__(self) -> RT:
        if not self._done:
            waiter = yield from GetTask().__await__()  # type: Task
            self._waiters.append(waiter)
            yield from Hibernate().__await__()
        value, exception = self._result
        if exception is None:
            return value
        else:
            raise exception

    def __repr__(self):
        return '<Task %s>' % name(self.coroutine)


def collect(*tasks: Task):
    results, errors = [], []
    for task in tasks:
        try:
            results.append(task.result)
        except Exception as err:
            errors.append(err)
    if errors:
        raise MultiError(*errors)
    else:
        return results


class Resumption(object):
    def __init__(self, target: Task, deadline: float, signal: Exception = None):
        self.target = target
        self.deadline = deadline
        self.signal = signal
        self._canceled = False

    def __bool__(self) -> bool:
        return not self._canceled

    def cancel(self):
        self._canceled = True

    def __repr__(self):
        return '<%s %s at %s%s%s>' % (
            self.__class__.__name__,
            self.target,
            self.deadline,
            '' if self.signal is None else ' via %s' % self.signal,
            '' if not self._canceled else ' (cancelled)'
        )


# Commands
class Hibernate(object):
    """Pause current execution"""
    def __await__(self):
        return (yield self)


class Schedule(object):
    """Schedule the resumption of an execution"""
    def __init__(self, target: Task = None, delay: float = 0, signal: Exception = None):
        self.target = target
        self.signal = signal
        self.delay = delay

    def __await__(self) -> Resumption:
        return (yield self)


class GetTime(object):
    """Get the current time"""
    def __await__(self) -> float:
        return (yield self)


class GetTask(object):
    """Get the current Task"""
    def __await__(self) -> Task:
        return (yield self)
