from usim import time, Scope, ActivityState, instant

from ..utility import via_usim


async def sleep(duration):
    await (time + duration)
    return duration


class TestExecution:
    @via_usim
    async def test_await(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert time.now == 0
            # await inside scope
            await activity
            assert time.now == 20
        # await outside scope
        await activity
        assert time.now == 20

    @via_usim
    async def test_result(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert time.now == 0
            # await result inside scope
            assert await activity.result == 20
            # await result delayed us
            assert time.now == 20
        # await outside scope
        assert await activity.result == 20
        assert time.now == 20

    @via_usim
    async def test_state_success(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert activity.status == ActivityState.CREATED
            await instant
            assert activity.status == ActivityState.RUNNING
            await activity
            assert activity.status == ActivityState.SUCCESS
            assert activity.status & ActivityState.FINISHED

    @via_usim
    async def test_state_cancel_created(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert activity.status == ActivityState.CREATED
            activity.cancel()
            # early cancellation does not run
            assert activity.status == ActivityState.CANCELLED
            await instant
            assert activity.status == ActivityState.CANCELLED
            await activity
            assert activity.status == ActivityState.CANCELLED
            assert activity.status & ActivityState.FINISHED

    @via_usim
    async def test_state_cancel_running(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert activity.status == ActivityState.CREATED
            await instant
            assert activity.status == ActivityState.RUNNING
            activity.cancel()
            # running cancellation is graceful
            assert activity.status == ActivityState.RUNNING
            await activity
            assert activity.status == ActivityState.CANCELLED
            assert activity.status & ActivityState.FINISHED

    @via_usim
    async def test_condition(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert bool(activity) is False
            assert bool(~activity) is True
            # waiting for inverted, unfinished activity does not delay
            assert await (~activity) is True
            assert time.now == 0
            await (time + 10)
            assert bool(activity) is False
            assert bool(~activity) is True
            assert await (~activity) is True
            assert time.now == 10
            await (time + 10)
            assert bool(activity) is True
            assert bool(~activity) is False
            assert await activity is True
            assert time.now == 20
