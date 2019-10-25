import inspect

import pytest

from usim import Scope, time, instant, Concurrent

from ..utility import via_usim, assertion_mode


async def async_raise(exc: BaseException, after=0):
    """Raise an exception in an ``await`` or ``scope.do`` context"""
    if after:
        await (time + after)
    raise exc


async def async_pass():
    pass


class TestExceptions:
    @via_usim
    async def test_fail_scope(self):
        """Failure inside the scope cancels children"""
        observations = 0

        async def observe(after):
            nonlocal observations
            await (time + after)
            observations += 1

        with pytest.raises(KeyError):
            async with Scope() as scope:
                scope.do(observe(5))
                await instant
                await observe(5)
                assert observations == 2
                scope.do(observe(5))
                await instant
                raise KeyError
        assert observations == 2

    @via_usim
    async def test_fail_child(self):
        """Failure inside a child fails the scope"""
        observations = 0

        async def observe(after):
            nonlocal observations
            await (time + after)
            observations += 1

        with pytest.raises(Concurrent):
            async with Scope() as scope:
                scope.do(observe(5))
                await instant
                await observe(5)
                assert observations == 2
                scope.do(async_raise(KeyError()))
                await instant
                await observe(5)
        assert observations == 2

    @via_usim
    async def test_fail_children(self):
        """Failure inside children fails the scope"""
        observations = 0

        async def observe(after):
            nonlocal observations
            await (time + after)
            observations += 1

        with pytest.raises(Concurrent):
            async with Scope() as scope:
                scope.do(observe(5))
                await instant
                await observe(5)
                assert observations == 2
                scope.do(async_raise(KeyError()))
                scope.do(async_raise(IndexError()))
                await instant
                await observe(5)
        assert observations == 2

    @via_usim
    async def test_fail_specialisation(self):
        """Failure inside children can be caught specifically"""
        with pytest.raises(KeyError):
            async with Scope() as scope:
                scope.do(async_raise(IndexError(), 1))
                raise KeyError
        assert time.now == 0

        with pytest.raises(Concurrent[IndexError]):
            async with Scope() as scope:
                scope.do(async_raise(IndexError(), 1))
                scope.do(async_raise(KeyError(), 2))
                scope.do(async_raise(ValueError(), 2))
                await (time + 2)
                raise KeyError
        assert time.now == 1

        with pytest.raises(Concurrent[IndexError, TypeError]):
            async with Scope() as scope:
                scope.do(async_raise(IndexError(), 1))
                scope.do(async_raise(TypeError(), 1))
                scope.do(async_raise(KeyError(), 2))
                scope.do(async_raise(ValueError(), 2))
                await (time + 2)
                raise KeyError
        assert time.now == 2

        with pytest.raises(Concurrent[IndexError, TypeError, ...]):
            async with Scope() as scope:
                scope.do(async_raise(IndexError(), 1))
                scope.do(async_raise(TypeError(), 1))
                scope.do(async_raise(KeyError(), 1))
                scope.do(async_raise(ValueError(), 2))
                await (time + 2)
                raise KeyError
        assert time.now == 3

    @via_usim
    async def test_fail_privileged(self):
        """Failure inside children with privileged errors is not collapsed"""
        for exc_type in (AssertionError, KeyboardInterrupt, SystemExit):
            with pytest.raises(exc_type):
                async with Scope() as scope:
                    scope.do(async_raise(IndexError(), 0))
                    scope.do(async_raise(TypeError(), 0))
                    scope.do(async_raise(KeyError(), 0))
                    scope.do(async_raise(exc_type(), 0))
            with pytest.raises(exc_type):
                async with Scope() as scope:
                    scope.do(async_raise(IndexError(), 0))
                    scope.do(async_raise(TypeError(), 0))
                    scope.do(async_raise(KeyError(), 0))
                    raise exc_type


class TestScoping:
    @via_usim
    async def test_do_after(self):
        async with Scope() as scope:
            apass = scope.do(async_pass(), after=10)
            assert time.now == 0
            await apass
            assert time.now == 10
            # zero delay is well-defined
            apass = scope.do(async_pass(), after=0)
            assert time.now == 10
            await apass
            assert time.now == 10

    @via_usim
    async def test_do_at(self):
        async with Scope() as scope:
            apass = scope.do(async_pass(), at=10)
            assert time.now == 0
            await apass
            assert time.now == 10
            # zero delay is well-defined
            apass = scope.do(async_pass(), at=10)
            assert time.now == 10
            await apass
            assert time.now == 10

    @assertion_mode
    @via_usim
    async def test_do_misuse(self):
        fail_pass = async_pass()
        with pytest.raises(AssertionError):
            async with Scope() as scope:
                scope.do(fail_pass, at=-1)
        with pytest.raises(AssertionError):
            async with Scope() as scope:
                scope.do(fail_pass, after=-1)
        fail_pass.close()

    @via_usim
    async def test_teardown_late(self):
        """Test that the scope may receive failures during shutdown"""
        async def fail_late(scope):
            await scope
            raise KeyError

        with pytest.raises(Concurrent[KeyError]):
            async with Scope() as scope:
                scope.do(fail_late(scope))

    @via_usim
    async def test_spawn_late(self):
        """Test spawning during graceful shutdown"""
        async def spawn_late(scope):
            await scope
            scope.do(time + 10)

        async with Scope() as scope:
            scope.do(spawn_late(scope))
        assert time.now == 10

    @via_usim
    async def test_spawn_after_shutdown(self):
        async def activity(value):
            return value

        async with Scope() as scope:
            pass
        payload = activity(3)
        with pytest.raises(RuntimeError):
            scope.do(payload)
        assert inspect.getcoroutinestate(payload) == inspect.CORO_CLOSED

    @via_usim
    async def test_close_volatile(self):
        """All volatile children are closed at end of scope"""
        async def activity():
            await (time + 10)

        async with Scope() as scope:
            volatile_children = [scope.do(activity(), volatile=True) for _ in range(5)]
            for child in volatile_children:
                assert not child.done
        assert (time == 0)
        for child in volatile_children:
            assert child.done
