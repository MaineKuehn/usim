import pytest

from usim import time, until

from ..utility import via_usim


class TestTime:
    @via_usim
    async def test_misuse(self):
        with pytest.raises(TypeError):
            await time
        with pytest.raises(TypeError):
            await (time <= 100)

    @via_usim
    async def test_delay(self):
        start, delay = time.now, 20
        for seq in range(5):
            assert start + (delay * seq) == time.now
            await (time + delay)
        assert start + (delay * 5) == time.now

    @via_usim
    async def test_moment(self):
        start, delay = time.now, 20
        for seq in range(5):
            await (time == start + seq * delay)
            assert start + (delay * seq) == time.now
        assert start + (delay * 4) == time.now

    @via_usim
    async def test_previous_moment(self):
        start, delay = time.now, 20
        async with until(time == start + delay):
            await (time == start - 5)  # await moment in the past
            assert False, "Moment in the past should never pass"
        assert start + delay == time.now

    @via_usim
    async def test_after(self):
        start, delay = time.now, 20
        for seq in range(5):
            await (time >= start + seq * delay)
            assert start + (delay * seq) == time.now
        assert start + (delay * 4) == time.now

    @via_usim
    async def test_previous_after(self):
        start, delay = time.now, 20
        async with until(time == start + delay):
            await (time >= start - 5)  # await moment in the past
            assert True, "After in the past should always pass"
        assert start == time.now
