import time

import click


from usim.kernel import Now, Schedule, Kernel, Sleep, FifoLock


def report(cycles, steps, elapsed):
    print('duration %.4fs' % elapsed)
    print('cycles %d [%.1f/s]' % (cycles, cycles / elapsed))
    print('steps  %d [%.1f/s]' % (steps, steps / elapsed))


@click.group()
def cli():
    pass


@cli.command()
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
    report(cycles, steps, elapsed)


@cli.command()
@click.option('-h', '--height', default=10)
@click.option('-d', '--degree', default=2)
def multifork(height, degree):
    async def forker(depth=0, children=2):
        if depth <= 0:
            return
        for _ in range(children):
            await Schedule(forker(depth-1, children=children))

    kernel = Kernel()
    stime = time.time()
    cycles, steps = kernel.run(forker(height, degree))
    etime = time.time()
    elapsed = etime - stime
    report(cycles, steps, elapsed)


@cli.command()
@click.option('-c', '--congestion', default=3)
@click.option('-a', '--acquires', default=3)
# @click.option('-t', '--type', 'flavour', default='fifo', type=click.Choice(['fifo', 'rand']))
def multilock(congestion=3, acquires=3):
    async def locker(idx, lock, count):
        for repetition in range(count):
            async with lock:
                print(idx, '=>', repetition, '@', await Now())
                await Sleep(1)

    kernel = Kernel()
    stime = time.time()
    lock = FifoLock()
    cycles, steps = kernel.run(*(locker(i, lock, acquires) for i in range(congestion)))
    etime = time.time()
    elapsed = etime - stime
    report(cycles, steps, elapsed)


if __name__ == "__main__":
    cli()
