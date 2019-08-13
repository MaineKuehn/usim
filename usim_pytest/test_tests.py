import pytest

from usim import Scope, eternity

from .utility import via_usim, UnfinishedTest


async def a_raise(exc: BaseException):
    """Raise an exception in an ``await`` or ``scope.do`` context"""
    raise exc


class TestTests:
    """Test propagation of test exceptions/signals"""
    @pytest.mark.xfail(strict=True)
    @via_usim
    async def test_run(self):
        """Test failure in a top-level activity"""
        assert False

    @pytest.mark.xfail(raises=KeyError, strict=True)
    @via_usim
    async def test_scoped(self):
        async with Scope() as scope:
            scope.do(a_raise(KeyError()))

    @pytest.mark.xfail(raises=UnfinishedTest, strict=True)
    @via_usim
    async def test_hanging(self):
        await eternity
