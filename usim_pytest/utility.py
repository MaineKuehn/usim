from typing import Callable, Coroutine, TypeVar
from functools import wraps
from collections import namedtuple

import pytest

from usim import run
from usim._core.handler import __USIM_STATE__


RT = TypeVar('RT')


Turnstamp = namedtuple('Turnstamp', ('time', 'turn'))


class UnfinishedTest(RuntimeError):
    """A test did never finish"""
    def __init__(self, test_case):
        self.test_case = test_case
        super().__init__('Test case %r did not finish' % getattr(
            test_case, '__name__', test_case
        ))


def noop(*args, **kwargs):
    """Placeholder callable that does nothing for any input"""
    pass


def turnstamp() -> Turnstamp:
    """Get the precise progress as ``time, turn``"""
    loop = __USIM_STATE__.loop
    return Turnstamp(loop.time, loop.turn)


def assert_postpone(allow_suspension=False):
    """
    Context to check whether its block did postpone

    :param allow_suspension: whether suspension is counted as suspending
    """
    return PostponesContext(allow_suspension=allow_suspension)


class PostponesContext:
    __slots__ = 'allow_suspension', 'start'

    def __init__(self, allow_suspension=False):
        self.allow_suspension = allow_suspension
        self.start = Turnstamp(0, 0)

    def __enter__(self):
        self.start = turnstamp()

    def __exit__(self, exc_type, exc_val, exc_tb):
        __tracebackhide__ = True
        start = self.start
        end = turnstamp()
        if self.allow_suspension:
            if not end > start:
                pytest.fail("Block failed to postpone or suspend")
        else:
            if end.time > start.time:
                pytest.fail("Block failed to postpone but suspended instead")
            elif not end.turn > start.turn:
                pytest.fail("Block failed to postpone but resumed immediately instead")


def assertion_mode(test_case: Callable[..., RT]) -> Callable[..., RT]:
    """
    Mark a test as using the optional assertion API only available in __debug__

    .. code:: python3

        @assertion_mode
        @via_usim
        async def test_do_assert(self):
            async with Scope() as scope:
                with pytest.raises(AssertionError):
                    scope.do(time + 3, after=-1)

    :note: This is intended to protect *app-level* assertions.
           The ``assert`` statements of pytest are not affected by debug mode.
    """
    if __debug__:
        return test_case
    return noop


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
        test_completed = False

        async def complete_test_case():
            nonlocal test_completed
            await test_case(*args, **kwargs)
            test_completed = True
        run(complete_test_case())
        if not test_completed:
            raise UnfinishedTest(test_case)
    return run_test
