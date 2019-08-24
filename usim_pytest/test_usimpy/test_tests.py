import pytest

from usim.py import Environment

from .utility import via_usimpy, UnfinishedTest


class TestTests:
    """Test propagation of test exceptions/signals"""
    @pytest.mark.xfail(strict=True)
    @via_usimpy
    def test_failure(self, env: Environment):
        """Test failure in a top-level activity"""
        assert False

    @pytest.mark.xfail(raises=UnfinishedTest, strict=True)
    @via_usimpy
    def test_hanging(self, env: Environment):
        """Test waiting on untriggered event"""
        yield env.event()
