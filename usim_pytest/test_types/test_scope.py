import pytest

from usim import Scope, time, instant, Concurrent

from ..utility import via_usim


async def async_raise(exc: BaseException, after=0):
    """Raise an exception in an ``await`` or ``scope.do`` context"""
    if after:
        await (time + after)
    raise exc


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
