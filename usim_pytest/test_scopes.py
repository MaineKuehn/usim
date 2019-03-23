from usim import Scope

from .utility import via_usim


@via_usim
async def test_do():
    async def payload():
        return 2

    async with Scope() as scope:
        activity = scope.do(payload())

    assert await activity.result == 2
