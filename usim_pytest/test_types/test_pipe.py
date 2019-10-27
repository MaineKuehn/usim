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

    @via_usim
    async def test_stream_uncontested(self):
        pipe = Pipe(throughput=2)
        async for idx, _ in aenumerate(pipe.stream(each=0.5, total=1, throughput=1), 1):
            assert (time == idx * 0.5)
        async for idx, _ in aenumerate(pipe.stream(each=0.5, total=1), 1):
            assert (time == idx * 0.25 + 1)

    @via_usim
    async def test_stream_contested(self):
        async def assert_stream(stream, delta):
            async for idx, _ in aenumerate(stream, 1):
                assert (time == idx * delta)

        pipe = Pipe(throughput=2)
        async with Scope() as scope:
            scope.do(assert_stream(pipe.stream(each=1, total=10), 1))
            scope.do(assert_stream(pipe.stream(each=1, total=10), 1))
        assert (time == 10)
