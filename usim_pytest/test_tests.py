import pytest

from usim import Scope, eternity, Concurrent

from .utility import via_usim, UnfinishedTest


async def a_raise(exc: BaseException):
    """Raise an exception in an ``await`` or ``scope.do`` context"""
    raise exc


async def async_assert():
    """Fail an exception in an ``await`` or ``scope.do`` context"""
    assert False, 'async assertion'


class TestTests:
    """Test propagation of test exceptions/signals"""
    @pytest.mark.xfail(raises=AssertionError, strict=True)
    @via_usim
    async def test_run(self):
        """Test failure in a top-level activity"""
        assert False

    @pytest.mark.xfail(raises=AssertionError, strict=True)
    @via_usim
    async def test_scoped(self):
        async with Scope() as scope:
            scope.do(async_assert())

    @pytest.mark.xfail(raises=Concurrent[KeyError], strict=True)
    @via_usim
    async def test_concurrent_scoped(self):
        async with Scope() as scope:
            scope.do(a_raise(KeyError()))

    @pytest.mark.xfail(raises=UnfinishedTest, strict=True)
    @via_usim
    async def test_hanging(self):
        await eternity
