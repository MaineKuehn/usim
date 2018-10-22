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
            sleep_queue.push(now, TaskRoot(coroutine))
        while sleep_queue:
            cycles += 1
            self.now, _ = now, tasks = sleep_queue.pop()
            now *= resolution
            tasks = deque(tasks)
            while tasks:
                steps += 1
                task = tasks.popleft()  # type: TaskRoot
                for command in task.advance(now):
                    if isinstance(command, Sleep):
                        assert command.duration > 0
                        sleep_queue.push(math.ceil((now + command.duration) / resolution), task)
                    elif isinstance(command, Schedule):
                        if command.delay <= 0:
                            tasks.append(TaskRoot(command.coroutine))
                        else:
                            sleep_queue.push(math.ceil((now + command.delay) / resolution), TaskRoot(command.coroutine))
        return cycles, steps


class TaskRoot(object):
    """Root of an asynchronous execution tree"""
    def __init__(self, coroutine):
        self.coroutine = coroutine

    def advance(self, now):
        """Advance this task for the current time step"""
        message = None
        while True:
            try:
                result = self.coroutine.send(message)
            except StopIteration:
                return
            if isinstance(result, Now):
                message = now
            elif isinstance(result, Sleep):
                if result.duration <= 0:
                    message = None
                else:
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
