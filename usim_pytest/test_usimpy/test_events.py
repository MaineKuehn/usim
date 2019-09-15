import pytest


from usim import Scope, instant
from usim.py import Interrupt, Event
from usim.py.events import ConditionValue, Condition

from ..utility import via_usim
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

    @via_usimpy
    def test_callbacks(self, env):
        head = env.event()
        tail = env.event()
        head.callbacks.append(tail.trigger)
        head.succeed('Done')
        yield tail
        assert tail.value == head.value

    def test_fail_teardown(self, env):
        """Unhandled failure destroys the environment"""
        event = env.event()
        event.fail(KeyError())
        with pytest.raises(KeyError):
            env.run()

    def test_fail_defuse(self, env):
        """Defused failure preserves the environment"""
        event = env.event()
        event.fail(KeyError())
        event.defused = True
        env.run()
        assert type(event.value) == KeyError

    def test_misuse(self, env):
        event = env.event()
        event.succeed()
        with pytest.raises(RuntimeError):
            event.succeed()
        with pytest.raises(RuntimeError):
            event.fail(KeyError())
        event = env.event()
        with pytest.raises(ValueError):
            event.fail('Not an Exception')


class TestTimeout:
    def test_misuse(self, env):
        with pytest.raises(ValueError):
            env.timeout(-1)
        env.timeout(0)
        env.timeout(200)


class TestProcess:
    @via_usimpy
    def test_waitfor_passed_event(self, env):
        """Wait for an event that has passed already"""
        event = env.event()
        event.succeed()
        yield env.timeout(1)
        assert event.processed
        yield event

    def test_interrupt(self, env):
        def proc(env):
            with pytest.raises(Interrupt):
                yield env.timeout(1)

        process = env.process(proc(env))
        process.interrupt('interrupt')
        env.run()

    def test_interrupt_many(self, env):
        def proc(env):
            for _ in range(3):
                with pytest.raises(Interrupt):
                    yield env.timeout(1)

        process = env.process(proc(env))
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        env.run()

    @via_usimpy
    def test_interrupt_late(self, env):
        def proc(env):
            for _ in range(3):
                with pytest.raises(Interrupt):
                    yield env.timeout(1)
            return True  # noqa: B901

        process = env.process(proc(env))
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        yield process
        assert process.value is True
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        process.interrupt('interrupt')
        assert process.value is True

    @via_usimpy
    def test_active_process(self, env):
        def proc(env):
            assert env.active_process is process
            yield env.timeout(1)
            assert env.active_process is process
            yield env.timeout(1)
            assert env.active_process is process

        def watcher(env):
            assert env.active_process is not process
            yield env.timeout(1)
            assert env.active_process is not process
            yield env.timeout(1)
            assert env.active_process is not process

        process = env.process(proc(env))
        env.process(watcher(env))
        yield env.timeout(1)
        assert process.is_alive
        yield process
        assert not process.is_alive
        assert env.active_process is not process

    def test_env_exit(self, env):
        def proc(env):
            yield env.timeout(1)
            env.exit(42)

        process = env.process(proc(env))
        env.run(5)
        assert process.value == 42

    def test_error_raised(self, env):
        def proc(env):
            yield env.timeout(1)
            raise KeyError()

        process = env.process(proc(env))
        with pytest.raises(KeyError):
            env.run()
        assert env.now == 1
        assert type(process.value) == KeyError

    def test_generator(self, env):
        with pytest.raises(ValueError):
            env.process(lambda: None)
        with pytest.raises(ValueError):
            env.process(42)
        with pytest.raises(ValueError):
            env.process({'throw': True, 'send': True})

        class CustomGenerator:
            def throw(self, exception):
                return env.event()

            def send(self, value):
                return env.event()

        env.process(CustomGenerator())


class TestConditionValue:
    def test_operations(self, env):
        events = env.event().succeed(0), env.event().succeed(1)
        values = ConditionValue(*events)
        assert all(event in values for event in events)
        assert all(values[event] == event.value for event in events)
        for value, event in zip(values.values(), events):
            assert value == event.value
        with pytest.raises(KeyError):
            values[0]
        assert values == ConditionValue(*events)
        assert values == ConditionValue(*events).todict()


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
    def test_env_operator(self, env):
        assert env.now == 0
        yield env.any_of(env.timeout(delay) for delay in range(5, 11))
        assert env.now == 5
        yield env.all_of(env.timeout(delay) for delay in range(5, 11))
        assert env.now == 15

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

    @via_usimpy
    def test_fail_immediately(self, env):
        event = env.event()
        condition = env.timeout(5) & event & env.timeout(2000)
        event.fail(KeyError())  # fail before yielding control
        with pytest.raises(KeyError):
            yield condition

    @via_usimpy
    def test_succeed_never(self, env):
        events = tuple(env.event() for _ in range(4))
        condition = Condition(env, lambda events, count: False, events)
        assert not condition.triggered
        yield env.timeout(10)
        assert not condition.triggered


class TestUsim:
    @via_usim
    async def test_await_event_success(self, env):
        async def receiver(signal: Event):
            assert (await signal) == 42
            return True

        async with Scope() as scope:
            async with env:
                event = env.event()
                recv = scope.do(receiver(event))
                await instant
                event.succeed(42)
                received = await recv
                assert received

    @via_usim
    async def test_await_event_failure(self, env):
        async def receiver(signal: Event):
            with pytest.raises(KeyError):
                await signal
            return True

        async with Scope() as scope:
            async with env:
                event = env.event()
                recv = scope.do(receiver(event))
                await instant
                event.fail(KeyError())
                received = await recv
                assert received
