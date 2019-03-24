from typing import Callable, Coroutine
from functools import wraps

from usim import run


def via_usim(test_case: Callable[..., Coroutine]):
    """
    Mark an ``async def`` test case to be run via ``usim.run``

    .. code:: python3

        @via_usim
        async def test_sleep():
            before = time.now
            await (time + 20)
            after = time.now
            assert after - before == 20
    """
    @wraps(test_case)
    def run_test(*args, **kwargs):
        __tracebackhide__ = True
        return run(test_case(*args, **kwargs))
    return run_test
