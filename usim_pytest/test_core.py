from concurrent.futures import ThreadPoolExecutor

import pytest

from usim import time, run
from usim._core.loop import Loop, ActivityLeak
from usim._core.handler import __USIM_STATE__


class TestCore:
    def test_no_sim(self):
        with pytest.raises(RuntimeError):
            time.now
        for field in Loop.__slots__:
            with pytest.raises(RuntimeError):
                getattr(__USIM_STATE__.loop, field)

    def test_after_sim(self):
        run()
        self.test_no_sim()

    def test_exception(self):
        async def returning(value):
            return value

        with pytest.raises(ActivityLeak) as exc_info:
            run(returning(1138))
        assert exc_info.value.result == 1138

    def test_threaded(self):
        """Test that behaviour is consistent in threads"""
        with ThreadPoolExecutor() as executor:
            for test_case in (
                self.test_no_sim,
                self.test_after_sim,
                self.test_exception,
            ):
                threaded_test = executor.submit(test_case)
                threaded_test.result()
