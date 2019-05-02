import pytest

from usim import time
from usim._core.loop import __LOOP_STATE__, Loop


class TestCore:
    def test_no_sim(self):
        with pytest.raises(RuntimeError):
            time.now
        for field in Loop.__slots__:
            with pytest.raises(RuntimeError):
                getattr(__LOOP_STATE__.LOOP, field)
