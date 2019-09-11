from usim import Flag

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

