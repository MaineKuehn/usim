import math
from collections import deque

from .waitq import WaitQueue
from .utility import __repr__


class Kernel(object):
    def __init__(self, start=0, resolution=0.1):
        self.now = start
        self.resolution = resolution
        self._sleep_queue = WaitQueue()

    def run(self, *coroutines):
        cycles, steps = 0, 0
        sleep_queue, now, resolution = self._sleep_queue, self.now, self.resolution
        for coroutine in coroutines:
            sleep_queue.push(now, coroutine)
        while sleep_queue:
            cycles += 1
            self.now, _ = now, tasks = sleep_queue.pop()
            now *= resolution
            tasks = deque(tasks)
            while tasks:
                steps += 1
                task = tasks.popleft()
                for command in advance(task, now):
                    if isinstance(command, Sleep):
                        assert command.duration > 0
                        sleep_queue.push(math.ceil((now + command.duration) / resolution), task)
                    elif isinstance(command, Schedule):
                        if command.delay <= 0:
                            tasks.append(command.coroutine)
                        else:
                            sleep_queue.push(math.ceil((now + command.delay) / resolution), command.coroutine)
                    elif isinstance(command, Reschedule):
                        tasks.append(task)
                    else:
                        raise ValueError('unknown command %r' % command)
        return cycles, steps


def advance(coroutine, now):
    """Advance coroutine for the current time step"""
    message = None
    while True:
        try:
            result = coroutine.send(message)
        except StopIteration:
            return
        if isinstance(result, Now):
            message = now
        elif isinstance(result, __Stack__):
            message = coroutine
        elif isinstance(result, Lock):
            # the Lock owns the coroutine now
            break
        elif isinstance(result, Sleep):
            if result.duration <= 0:
                message = None
            else:
                yield result
                break
        elif isinstance(result, Reschedule):
            yield result
            break
        else:
            message = yield result


class Schedule(object):
    """Schedule another coroutine for execution and resume"""
    def __init__(self, coroutine, *, delay=0):
        self.coroutine = coroutine
        self.delay = delay

    def __await__(self):
        yield self

    __repr__ = __repr__


class Reschedule(object):
    """Reschedule the current coroutine in the same timestep"""
    def __await__(self):
        yield self

    __repr__ = __repr__


class Sleep(object):
    """Pause a coroutine for ``duration`` seconds"""
    def __init__(self, duration: float):
        assert duration > 0
        self.duration = duration

    def __await__(self):
        yield self

    __repr__ = __repr__


class Now(object):
    """Get the current time"""
    def __await__(self):
        return (yield self)

    __repr__ = __repr__


class __Stack__(object):
    """Get the current coroutine stack"""
    def __await__(self):
        return (yield self)

    __repr__ = __repr__


class Lock(object):
    def __await__(self):
        yield self


class FifoLock(Lock):
    def __init__(self):
        self.held = False
        self._waiters = deque()

    async def __aenter__(self):
        # uncontested - just take it
        if not self.held:
            self.held = True
            return
        # contested - store THIS STACK for resumption
        stack = await __Stack__()
        self._waiters.append(stack)
        await self  # break point - we are resumed when we own the lock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            waiter = self._waiters.popleft()
        except IndexError:
            # no one to inherit the lock - release it
            self.held = False
        else:
            await Schedule(waiter)
        # pass on any errors
        return False
