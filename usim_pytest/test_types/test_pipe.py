import pytest

from usim import time, Pipe, UnboundedPipe, Scope

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
    async def test_transfer_zero(self):
        pipe = Pipe(throughput=2)
        await pipe.transfer(total=0)
        assert (time == 0)

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

    @via_usim
    async def test_transfer_inexact(self):
        # Values adapted from MatterMiners/lapis#61
        # Need to advance the simulation time to have a lower
        # time resolution. This makes it more likely to round
        # down the calculated transfer time.
        await (time + 100)
        pipe = Pipe(throughput=10)
        async with Scope() as scope:
            for _ in range(6):
                scope.do(pipe.transfer(total=15))


class TestUnboundedPipe:
    @assertion_mode
    @via_usim
    async def test_debug_misuse(self):
        with pytest.raises(AssertionError):
            UnboundedPipe(throughput=0)
        with pytest.raises(AssertionError):
            UnboundedPipe(throughput=-10)
        with pytest.raises(AssertionError):
            UnboundedPipe(throughput=10)
        pipe = UnboundedPipe()
        with pytest.raises(AssertionError):
            await pipe.transfer(total=-10, throughput=20)
        with pytest.raises(AssertionError):
            await pipe.transfer(total=10, throughput=0)

    @via_usim
    async def test_transfers(self):
        pipe = UnboundedPipe()
        for total in (0, 10, float('inf')):
            await pipe.transfer(total=total)
        assert (time == 0)
        async with Scope() as scope:
            for total in (0, 10, float('inf')):
                scope.do(pipe.transfer(total=total))
                scope.do(pipe.transfer(total=total))
                scope.do(pipe.transfer(total=total))
                scope.do(pipe.transfer(total=total))
        assert (time == 0)


@pytest.mark.parametrize("pipe_type", [Pipe, UnboundedPipe])
@via_usim
async def test_infinite_transfers(pipe_type):
    pipe = pipe_type(throughput=float('inf'))
    await pipe.transfer(total=20)
    assert (time == 0)
    await pipe.transfer(total=20, throughput=10)
    assert (time == 2)
    await pipe.transfer(total=0, throughput=10)
    assert (time == 2)
