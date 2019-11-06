from usim import time, Pipe, Scope

from ..utility import via_usim


async def aenumerate(aiterable, start=0):
    count = start
    async for item in aiterable:
        yield count, item
        count += 1


class TestPipe:
    @via_usim
    async def test_transfer_uncontested(self):
        pipe = Pipe(throughput=2)
        await pipe.transfer(total=1, throughput=1)
        assert (time == 1)
        await pipe.transfer(total=2)
        assert (time == 2)
        async with Scope() as scope:
            scope.do(pipe.transfer(total=1, throughput=1))
            scope.do(pipe.transfer(total=1, throughput=1))
        assert (time == 3)
        async with Scope() as scope:
            scope.do(pipe.transfer(total=0.5, throughput=0.5))
            scope.do(pipe.transfer(total=0.5, throughput=0.5))
            scope.do(pipe.transfer(total=0.5, throughput=0.5))
            scope.do(pipe.transfer(total=0.5, throughput=0.5))
        assert (time == 4)
        async with Scope() as scope:
            scope.do(pipe.transfer(total=0.5, throughput=0.5))
            scope.do(pipe.transfer(total=0.5, throughput=0.5))
            scope.do(pipe.transfer(total=0.25, throughput=0.5))
            scope.do(pipe.transfer(total=0.25, throughput=0.5))
        assert (time == 5)

    @via_usim
    async def test_transfer_contested(self):
        pipe = Pipe(throughput=2)
        await pipe.transfer(total=2, throughput=4)
        assert (time == 1)
        await pipe.transfer(total=2, throughput=20)
        assert (time == 2)
        async with Scope() as scope:
            scope.do(pipe.transfer(total=1, throughput=2))
            scope.do(pipe.transfer(total=1, throughput=2))
        assert (time == 3)
        async with Scope() as scope:
            scope.do(pipe.transfer(total=1, throughput=2))
            scope.do(pipe.transfer(total=1, throughput=2))
            scope.do(pipe.transfer(total=1, throughput=2))
            scope.do(pipe.transfer(total=1, throughput=2))
        assert (time == 5)
        async with Scope() as scope:
            scope.do(pipe.transfer(total=2, throughput=2))
            scope.do(pipe.transfer(total=2, throughput=2))
            scope.do(pipe.transfer(total=1, throughput=2))
            scope.do(pipe.transfer(total=1, throughput=2))
        assert (time == 8)
