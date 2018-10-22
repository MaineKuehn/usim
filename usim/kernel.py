import time
import math
import sys
from collections import deque

from usim.waitq import WaitQueue
from usim.utility import __repr__


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
            self.now, _ = now, coroutines = sleep_queue.pop()
            now *= resolution
            coroutines = deque((coro, None) for coro in coroutines)
            while coroutines:
                steps += 1
                coroutine, message = coroutines.popleft()
                try:
                    command = coroutine.send(message)
                except StopIteration:
                    continue
                if isinstance(command, Sleep):
                    if command.duration <= 0:
                        coroutines.append((coroutine, None))
                    else:
                        sleep_queue.push(math.ceil((now + command.duration) / resolution), coroutine)
                elif isinstance(command, Schedule):
                    if command.delay <= 0:
                        coroutines.append((command.coroutine, None))
                    else:
                        sleep_queue.push(math.ceil((now + command.delay) / resolution), command.coroutine)
                    coroutines.append((coroutine, None))
                elif isinstance(command, Now):
                    coroutines.appendleft((coroutine, now))
        return cycles, steps


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


def multitask():
    async def sleeper(who: str, interval=1.5, count=10):
        for repetition in range(count):
            print('step %d at %s [%s] @ %.4f' % (repetition, await Now(), who, time.time()))
            await Sleep(interval)

    kernel = Kernel()
    stime = time.time()
    cycles, steps = kernel.run(sleeper('alice'), sleeper('micky'), sleeper('daisy'))
    etime = time.time()
    elapsed = etime - stime
    print('ran %d cycles, %d steps in %.4fs' % (cycles, steps, elapsed))
    print('%.1fc/s, %.1fs/s' % (cycles / elapsed, steps / elapsed))


def multifork():
    async def forker(depth=0, children=2):
        if depth <= 0:
            return
        for _ in range(children):
            await Schedule(forker(depth-1, children=children))

    kernel = Kernel()
    stime = time.time()
    cycles, steps = kernel.run(forker(20))
    etime = time.time()
    elapsed = etime - stime
    print('ran %d cycles, %d steps in %.4fs' % (cycles, steps, elapsed))
    print('%.1fc/s, %.1fs/s' % (cycles / elapsed, steps / elapsed))


if __name__ == "__main__":
    try:
        task = sys.argv[1]
    except IndexError:
        task = 'multifork'

    handles = {func.__name__: func for func in (multifork, multitask)}
    handles[task]()
