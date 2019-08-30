import pytest

from usim import Scope, time, instant, Concurrent

from ..utility import via_usim


async def async_raise(exc: BaseException):
    """Raise an exception in an ``await`` or ``scope.do`` context"""
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
