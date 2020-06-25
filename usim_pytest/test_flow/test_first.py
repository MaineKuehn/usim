import pytest

import asyncstdlib as a

from usim import first, time, Concurrent

from ..utility import via_usim


async def ping_pong(value, delay: float = 0.0):
    await (time + delay)
    return value


async def ping_raise(exception, delay: float = 0.0):
    await (time + delay)
    raise exception


@pytest.mark.parametrize('count', (5, 12, 1, 0))
@via_usim
async def test_collect_all(count):
    activities = [
        ping_pong(idx, delay=count - idx) for idx in range(count)
    ]
    async for winner, expected in a.zip(
            first(*activities, count=None), reversed(range(count))):
        assert winner == expected
    assert (time == count)


@pytest.mark.parametrize('count', (5, 12, 1))
@via_usim
async def test_collect_default(count):
    activities = [
        ping_pong(idx, delay=count - idx) for idx in range(count)
    ]
    async for winner in first(*activities):
        assert winner == count - 1
    assert (time == 1)


@pytest.mark.parametrize('count', (1, 0))
@via_usim
async def test_less_available(count):
    activities = [
        ping_pong(idx, delay=count - idx) for idx in range(count)
    ]
    with pytest.raises(ValueError):
        async for _ in first(*activities, count=3):
            pass
    assert (time == 0)
    # prevent resource warning from unhandled coroutines
    for activity in activities:
        activity.close()


@pytest.mark.parametrize('count', (5, 12, 1))
@via_usim
async def test_collect_failure(count):
    failures = (KeyError, IndexError, AttributeError)
    # abort on first failure
    with pytest.raises(Concurrent[KeyError]):
        activities = [
            ping_raise(failures[idx % 3], delay=idx) for idx in range(count)
        ]
        await a.list(first(*activities))
    # collect concurrent failures
    with pytest.raises(Concurrent[failures[:count]]):
        activities = [
            ping_raise(failures[idx % 3], delay=1) for idx in range(count)
        ]
        await a.list(first(*activities))
