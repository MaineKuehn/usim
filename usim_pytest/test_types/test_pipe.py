import pytest

from usim import time, Pipe, Scope

from ..utility import via_usim, assertion_mode


class TestPipe:
    @assertion_mode
    @via_usim
    async def test_debug_misuse(self):
        with pytest.raises(AssertionError):
            Pipe(throughput=0)
        with pytest.raises(AssertionError):
            Pipe(throughput=-10)
        pipe = Pipe(throughput=10)
        with pytest.raises(AssertionError):
            await pipe.transfer(total=-10, throughput=20)
        with pytest.raises(AssertionError):
            await pipe.transfer(total=10, throughput=0)

    @via_usim
    async def test_transfer_uncongested(self):
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
    async def test_transfer_congested(self):
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
