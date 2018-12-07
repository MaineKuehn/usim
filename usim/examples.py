import time as real_time
import random

import click


from usim.api import time, run, spawn, FifoLock, FifoEvent, Timeout


class Timed(object):
    def __init__(self):
        self._start = None
        self._stop = None

    @property
    def duration(self):
        if self._start is None or self._stop is None:
            raise RuntimeError('duration only available after use')
        return self._stop - self._start

    def __enter__(self):
        assert self._start is None
        self._start = real_time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._start is not None and self._stop is None
        self._stop = real_time.time()
        return False

    def __str__(self):
        if self._start is None:
            return '<untimed>'
        elif self._stop is None:
            return '<timing>'
        else:
            return '%.3fs' % self.duration


def report(duration, operations):
    print('total: %.3f' % duration)
    print('ops/s: %.3f' % (operations / duration))


@click.group()
def cli():
    pass


@cli.command()
def multitask():
    async def sleeper(who: str, interval=1.5, count=10):
        for repetition in range(count):
            print('step %d at simtime %s [%s] @ %.3f' % (repetition, await time(after=interval), who, real_time.time()))

    with Timed() as duration:
        run(sleeper('alice'), sleeper('micky'), sleeper('daisy'))
    report(duration.duration, 3 * 10)


@cli.command()
@click.option('-h', '--height', default=10)
@click.option('-d', '--degree', default=2)
def multifork(height, degree):
    async def forker(depth=0, children=2, *, child_idx=0):
        if depth <= 0:
            return
        for idx in range(children):
            await spawn(forker(depth-1, children=children, child_idx=idx + child_idx))
        if child_idx == 0:
            print('depth %3d done @ %.3fs' % (depth, real_time.time()))

    with Timed() as duration:
        run(forker(height, degree))
    report(duration.duration, (degree ** height) * 2 - 1)


@cli.command()
@click.option('-c', '--congestion', default=3)
@click.option('-a', '--acquires', default=3)
def multilock(congestion=3, acquires=3):
    async def locker(idx, lock, count):
        for repetition in range(count):
            async with lock:
                print('task', idx, '=> got', repetition, 'at simtime', await time(1))

    lock = FifoLock()
    with Timed() as duration:
        run(*(locker(i, lock, acquires) for i in range(congestion)))
    report(duration.duration, congestion * acquires)


@cli.command()
def multievent(waiters=100, toggle=0.5):
    async def reset(event):
        await event.clear()
        await event.set()

    async def waiter(idx, event, chance):
        while not event:
            await event
        if random.random() < chance:
            await event.clear()
            await spawn(reset(event), after=10)
        print(idx, 'done at', await time())

    event = FifoEvent()
    with Timed() as duration:
        run(spawn(reset(event), 10), *(waiter(i, event, toggle) for i in range(waiters)))
    report(duration.duration, waiters * 1 / toggle)


@cli.command()
def multitime(players=10, timeout=90):
    async def player(identifier, ball: FifoLock, fumbles=0.1):
        while True:
            async with ball:  # unconditionally wait for the ball to be available
                if random.random() > 1 / players:  # chance that someone else got the ball
                    continue
                print(identifier, 'got the ball at', await time())
                await time(after=1)
                while random.random() < fumbles:
                    await time(after=1)

    async def game(participants, duration):
        ball = FifoLock()
        async with Timeout(after=duration):
            players = []
            for idx in range(participants):
                players.append(await spawn(player(idx, ball)))
            await players[0]

    with Timed() as duration:
        run(game(participants=players, duration=timeout))
    report(
        duration.duration,
        players * (1 + (
            0 if players <= 1 else (1 / (players - 1)) ** players)
        )
    )


if __name__ == "__main__":
    cli()
