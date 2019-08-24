from functools import wraps
from typing import Callable, Generator

from ..utility import UnfinishedTest


def via_usimpy(test_case: Callable[..., Generator]):
    """
    Mark a generator function test case to be run via a ``usim.py.Environment``

    .. code:: python3

        @via_usimpy
        def test_sleep(env):
            before = env.now
            yield env.timeout(20)
            after = env.now
            assert after - before == 20

    Note that ``env`` is passed in as a keyword argument.
    """
    @wraps(test_case)
    def run_test(self=None, env=None, **kwargs):
        test_completed = False
        if self is not None:
            kwargs['self'] = self

        def complete_test_case():
            __tracebackhide__ = True
            nonlocal test_completed
            yield from test_case(env=env, **kwargs)
            test_completed = True
        __tracebackhide__ = True
        env.process(complete_test_case())
        result = env.run()
        if not test_completed:
            raise UnfinishedTest(test_case)
        return result
    return run_test
