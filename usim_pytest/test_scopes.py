import pytest

from usim import Scope, time, eternity, VolatileActivityExit, ActivityState

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
        assert activity.status == ActivityState.CREATED
        await (time + 4)
        assert activity.status == ActivityState.CREATED
        await (time + 3)
        assert activity.status == ActivityState.RUNNING
        await activity.result
        assert time.now == 15
        assert activity.status == ActivityState.SUCCESS


@via_usim
async def test_at():
    async def payload(duration):
        await (time + duration)

    async with Scope() as scope:
        activity_one = scope.do(payload(10), at=5)
        activity_two = scope.do(payload(15), at=5)
        await (activity_one | activity_two)
        assert time.now == 15
        await (activity_one & activity_two)
        assert time.now == 20


@via_usim
async def test_volatile():
    async def payload():
        await eternity
        return 2

    async with Scope() as scope:
        activity = scope.do(payload(), volatile=True)
    with pytest.raises(VolatileActivityExit):
        assert await activity.result
    assert activity.status == ActivityState.FAILED


@via_usim
async def test_after_and_at():
    async def payload():
        return 2

    async with Scope() as scope:
        with pytest.raises(ValueError):
            scope.do(payload(), after=1, at=1)
