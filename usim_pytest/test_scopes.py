import pytest

from usim import Scope, time

from .utility import via_usim


@via_usim
async def test_do():
    async def payload():
        return 2

    async with Scope() as scope:
        activity = scope.do(payload())

    assert await activity.result == 2


@via_usim
async def test_negative():
    async def payload():
        return 2

    async with Scope() as scope:
        with pytest.raises(AssertionError):
            scope.do(payload(), after=-1)
        with pytest.raises(AssertionError):
            scope.do(payload(), at=-1)


@via_usim
async def test_after():
    async def payload():
        await (time + 10)

    async with Scope() as scope:
        activity = scope.do(payload(), after=5)
        await (time + 4)
        # TODO: check that activity is not running
        await activity.result
        assert time.now == 15


@via_usim
async def test_at():
    async def payload(duration):
        await (time + duration)

    async with Scope() as scope:
        activity_one = scope.do(payload(10), at=5)
        activity_two = scope.do(payload(15), at=5)
        await (activity_one | activity_two)
        assert time.now == 15
        await (activity_one | activity_two)
        assert time.now == 20
