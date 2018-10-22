import time
import sys

import click


from usim.kernel import Now, Schedule, Kernel, Sleep


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
    print('ran %d cycles, %d steps in %.4fs' % (cycles, steps, elapsed))
    print('%.1fc/s, %.1fs/s' % (cycles / elapsed, steps / elapsed))


@cli.command()
@click.option('--depth', default=10)
@click.option('--degree', default=2)
def multifork(depth, degree):
    async def forker(depth=0, children=2):
        if depth <= 0:
            return
        for _ in range(children):
            await Schedule(forker(depth-1, children=children))

    kernel = Kernel()
    stime = time.time()
    cycles, steps = kernel.run(forker(depth, degree))
    etime = time.time()
    elapsed = etime - stime
    print('ran %d cycles, %d steps in %.4fs' % (cycles, steps, elapsed))
    print('%.1fc/s, %.1fs/s' % (cycles / elapsed, steps / elapsed))


if __name__ == "__main__":
    cli()
