from usim import time, Scope

from ..utility import via_usim


class TestExecution:
    @via_usim
    async def test_await(self):
        async with Scope() as scope:
            activity = scope.do(time + 20)
            assert time.now == 0
            # await inside scope
            await activity
            assert time.now == 20
        # await outside scope
        await activity
        assert time.now == 20

