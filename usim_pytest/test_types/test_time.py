import math
import sys

import pytest

from usim import time, until, eternity, instant

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

    @via_usim
    async def test_before(self):
        start, delay = time.now, 20
        for seq in range(5):
            await (time < start + seq * delay)
            assert start == time.now
        assert start == time.now

    @via_usim
    async def test_previous_before(self):
        start, delay = time.now, 20
        async with until(time == start + delay):
            await (time < start - 5)  # await moment in the past
            assert False, "Before in the past should never pass"
        assert start + delay == time.now

    @via_usim
    async def test_eternity_eq(self):
        async with until(time == sys.float_info.max):
            await (time == math.inf)  # await moment in the past
            assert False, "Eternity should never pass"
        assert math.inf > time.now

    @via_usim
    async def test_eternity_ge(self):
        async with until(time >= sys.float_info.max):
            await (time >= math.inf)  # await moment in the past
            assert False, "Eternity should never pass"
        assert math.inf > time.now


class TestTimeCondition:
    @via_usim
    async def test_after(self):
        start = time.now
        assert (time >= time.now)
        assert not (time >= time.now + 20)
        assert not ~(time >= time.now)
        assert ~(time >= time.now + 20)
        await (time >= time.now)
        await (time >= time.now + 20)
        assert time.now == start + 20

    @via_usim
    async def test_before(self):
        start = time.now
        assert not (time < time.now)
        assert (time < time.now + 20)
        assert ~(time < time.now)
        assert not ~(time < time.now + 20)
        await (time < time.now + 20)
        async with until(time + 20):
            await (time < time.now)
        assert time.now == start + 20

    @via_usim
    async def test_moment(self):
        start = time.now
        assert (time == start)
        assert not (time == start + 20)
        await (time == start + 20)
        assert not (time == start)
        assert (time == start + 20)
        assert time.now == start + 20

    @via_usim
    async def test_extremes(self):
        start = time.now
        assert instant
        assert not eternity
        assert not ~instant
        assert ~eternity
        await (time == start + 20)
        assert instant
        assert not eternity
        assert not ~instant
        assert ~eternity
        assert time.now == start + 20
