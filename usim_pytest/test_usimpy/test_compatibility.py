import pytest
from usim import Flag, time
from usim.py import Interrupt

from ..utility import assertion_mode
from .utility import via_usimpy


class TestUsim2Simpy:
    @via_usimpy
    def test_flag(self, env):
        """Can trigger and set flags"""
        flag = Flag()
        assert not flag

        def trigger_flag(after):
            yield env.timeout(after)
            yield flag.set()
        env.process(trigger_flag(5))
        yield flag
        assert env.now == 5

    @via_usimpy
    def test_coroutine(self, env):
        """Can yield-as-await coroutines"""
        assert env.now == 0

        async def ping_pong(value):
            return value
        result = yield ping_pong(3)
        assert result == 3
        assert env.now == 0

    @via_usimpy
    def test_time(self, env):
        """Can yield-as-await time expressions"""
        assert env.now == 0
        yield (time + 3)
        assert env.now == 3
        yield (time == 10)
        assert env.now == 10
        yield (time >= 20)
        assert env.now == 20
        yield (time >= 20)
        assert env.now == 20
        yield (time >= 10)
        assert env.now == 20

    @assertion_mode
    @via_usimpy
    def test_protection(self, env):
        """Test that usage errors propagate to simpy"""
        assert env.now == 0
        with pytest.raises(AssertionError):
            yield (time + -10)
        assert env.now == 0
        yield (time + 10)
        assert env.now == 10

    def test_interrupt(self, env):
        """Can interrupt yield-as-await delays"""
        def proc(env):
            with pytest.raises(Interrupt):
                yield (time + 1)

        process = env.process(proc(env))
        process.interrupt('interrupt')
        env.run()

    def test_interrupt_many(self, env):
        """Can interrupt yield-as-await delays"""
        def proc(env):
            for _ in range(3):
                with pytest.raises(Interrupt):
                    yield (time + 1)

        process = env.process(proc(env))
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        env.run()
