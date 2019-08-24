import pytest


from .utility import via_usimpy


class TestEvent:
    @via_usimpy
    def test_event_lifetime(self, env):
        event = env.event()
        assert not event.triggered
        assert not event.processed
        assert not event.ok
        event.succeed()
        assert event.triggered
        assert not event.processed
        assert event.ok
        yield event
        assert event.triggered
        assert event.processed
        assert event.ok

    @via_usimpy
    def test_event_lifetime_failure(self, env):
        event = env.event()
        assert not event.triggered
        assert not event.processed
        assert not event.ok
        event.fail(KeyError())
        event.defused = True
        assert event.triggered
        assert not event.processed
        assert not event.ok
        with pytest.raises(KeyError):
            yield event
        assert event.triggered
        assert event.processed
        assert not event.ok

    def test_event_value(self, env):
        event = env.event()
        with pytest.raises(AttributeError):
            event.value
        event.succeed('Success!')
        assert event.value == 'Success!'
        event = env.event()
        event.fail(KeyError())
        event.defused = True
        assert type(event.value) == KeyError

    def test_notification(self, env):
        event = env.event()

        def sender(env, event):
            yield env.timeout(5)
            event.succeed('done')

        def receiver(env, event):
            value = yield event
            assert value == 'done'
            yield env.timeout(5)

        env.process(sender(env, event))
        env.process(receiver(env, event))
        env.run()
        assert env.now == 10


class TestCondition:
    @via_usimpy
    def test_operator_or(self, env):
        timeouts = (
            env.timeout(4)
            | env.timeout(2)
            | env.timeout(1)
            | env.timeout(3)
            | env.timeout(4)
        )
        assert env.now == 0
        yield timeouts
        assert env.now == 1

    @via_usimpy
    def test_operator_and(self, env):
        timeouts = (
            env.timeout(4)
            & env.timeout(2)
            & env.timeout(1)
            & env.timeout(3)
            & env.timeout(4)
        )
        assert env.now == 0
        yield timeouts
        assert env.now == 4

    @via_usimpy
    def test_operator_inplace(self, env):
        timeouts = env.timeout(4)
        timeouts &= env.timeout(2)
        timeouts &= env.timeout(1)
        timeouts &= env.timeout(3)
        timeouts &= env.timeout(4)
        assert env.now == 0
        yield timeouts
        assert env.now == 4

    @via_usimpy
    def test_value_flat(self, env):
        timeouts = env.timeout(1, 1), env.timeout(2, 2)
        result = yield (timeouts[0] | timeouts[1])
        assert result.todict() == {
            timeouts[0]: 1,
        }

    @via_usimpy
    def test_value_nested(self, env):
        timeouts = env.timeout(1, 1), env.timeout(2, 2), env.timeout(3, 3)
        result = yield ((timeouts[0] | timeouts[2]) & timeouts[1])
        assert result.todict() == {
            timeouts[0]: 1,
            timeouts[1]: 2,
        }

    @via_usimpy
    def test_error(self, env):
        def fail_after(env, event, delay):
            yield env.timeout(delay)
            event.fail(KeyError())
        event = env.event()
        condition = env.timeout(5) & event & env.timeout(2000)
        env.process(fail_after(env, event, 1))
        with pytest.raises(KeyError):
            yield condition
        assert env.now == 1
        assert condition.triggered
        assert not condition.ok
        assert type(event.value) == KeyError
        assert event.value == condition.value
