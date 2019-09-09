import pytest

from usim import Scope, time
from usim.py import Environment
from usim.py.exceptions import NotCompatibleError

from ..utility import via_usim


class TestEnvironment:
    def test_events_done(self, env):
        """env.run() stops automatically when all events are done"""
        # side-effect to ensure something *is* run
        def observable(env, log: list):
            log.append(1)
            yield env.timeout(1)
            log.append(2)
            yield env.timeout(1)

        output = []
        env.process(observable(env, output))
        env.run()
        assert output == [1, 2]
        assert env.now == 2

    def test_until_past(self, env):
        """env.run(until) argument must not be in the past"""
        with pytest.raises(ValueError):
            env.run(-5)

    def test_until_future(self, env):
        assert env.now == 0
        env.run(15)
        assert env.now == 15

    def test_until_now(self, env):
        assert env.now == 0
        env.run(0)
        assert env.now == 0

    def test_until_event(self, env):
        timeout = env.timeout(1, 'Hello World')
        result = env.run(timeout)
        assert env.now == 1
        assert result == 'Hello World'

    def test_until_not_triggered(self, env):
        event = env.event()
        with pytest.raises(RuntimeError):
            env.run(event)

    def test_inital_time(self):
        env = Environment(25)
        assert env.now == 25
        env.run(50)
        assert env.now == 50
        env = Environment(25)
        assert env.now == 25
        with pytest.raises(ValueError):
            env.run(10)

    @via_usim
    async def test_inside_usim(self, env):
        with pytest.raises(NotCompatibleError):
            env.run()

    @via_usim
    async def test_no_duplication(self, env):
        async def run_env():
            async with env:
                await (time + 10)

        async def fail_env():
            with pytest.raises(RuntimeError):
                async with env:
                    await (time + 10)

        async with Scope() as scope:
            run = scope.do(run_env())
            fail = scope.do(fail_env())
            await fail
            assert time.now == 0
            await run
            assert time.now == 10
