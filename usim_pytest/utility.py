from typing import Callable, Coroutine, TypeVar
from functools import wraps
from collections import namedtuple

from usim import run
from usim._core.loop import ActivityError, __LOOP_STATE__


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
    loop = __LOOP_STATE__.LOOP
    return Turnstamp(loop.time, loop.turn)


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
        # pytest currently ignores __tracebackhide__ if we re-raise
        # https://github.com/pytest-dev/pytest/issues/1904
        __tracebackhide__ = True
        # >>> This is not the frame you are looking for. Do read on. <<<
        try:
            result = run(complete_test_case())
        except ActivityError as err:
            # unwrap any exceptions
            raise err.__cause__
        else:
            if not test_completed:
                raise UnfinishedTest(test_case)
            return result
    return run_test
