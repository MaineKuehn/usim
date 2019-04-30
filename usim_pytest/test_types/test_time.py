import pytest

from usim import time

from ..utility import via_usim


class TestTime:
    @via_usim
    async def test_misuse(self):
        with pytest.raises(TypeError):
            await time

    @via_usim
    async def test_delay(self):
        start, delay = time.now, 20
        for seq in range(5):
            assert start + (delay * seq) == time.now
            await (time + delay)
        assert start + (delay * 5) == time.now
