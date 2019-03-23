from typing import Callable, Coroutine
from functools import wraps

from usim import run


def via_usim(test_case: Callable[..., Coroutine]):
    @wraps(test_case)
    def run_test():
        return run(test_case())
    return run_test
