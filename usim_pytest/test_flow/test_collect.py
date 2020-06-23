import pytest

from usim import collect, time, Concurrent

from ..utility import via_usim


async def ping_pong(value, delay: float = 0.0):
    await (time + delay)
    return value


async def ping_raise(exception, delay: float = 0.0):
    await (time + delay)
    raise exception


@pytest.mark.parametrize('count', (5, 12, 1, 0))
@via_usim
async def test_collect_some(count):
    activities = [
        ping_pong(idx, delay=count - idx) for idx in range(count)
    ]
    assert await collect(*activities) == list(range(count))
    assert (time == count)


@pytest.mark.parametrize('count', (5, 12, 1))
@via_usim
async def test_collect_failure(count):
    failures = (KeyError, IndexError, AttributeError)
    # abort on first failure
    with pytest.raises(Concurrent[KeyError]):
        activities = [
            ping_raise(failures[idx % 3], delay=idx) for idx in range(count)
        ]
        await collect(*activities)
    # collect concurrent failures
    with pytest.raises(Concurrent[failures[:count]]):
        activities = [
            ping_raise(failures[idx % 3], delay=1) for idx in range(count)
        ]
        await collect(*activities)
