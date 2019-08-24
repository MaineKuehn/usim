import pytest


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

    def test_until_event(self, env):
        timeout = env.timeout(1, 'Hello World')
        result = env.run(timeout)
        assert env.now == 1
        assert result == 'Hello World'
