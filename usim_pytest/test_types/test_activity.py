from usim import time, Scope, TaskState, instant

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
            await activity.done
            assert time.now == 20
        # await outside scope
        await activity.done
        assert time.now == 20

    @via_usim
    async def test_result(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert time.now == 0
            # await result inside scope
            assert await activity == 20
            # await result delayed us
            assert time.now == 20
        # await outside scope
        assert await activity == 20
        assert time.now == 20

    @via_usim
    async def test_state_success(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert activity.status == TaskState.CREATED
            await instant
            assert activity.status == TaskState.RUNNING
            await activity.done
            assert activity.status == TaskState.SUCCESS
            assert activity.status & TaskState.FINISHED

    @via_usim
    async def test_state_cancel_created(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert activity.status == TaskState.CREATED
            activity.cancel()
            # early cancellation does not run
            assert activity.status == TaskState.CANCELLED
            await instant
            assert activity.status == TaskState.CANCELLED
            await activity.done
            assert activity.status == TaskState.CANCELLED
            assert activity.status & TaskState.FINISHED

    @via_usim
    async def test_state_cancel_running(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            assert activity.status == TaskState.CREATED
            await instant
            assert activity.status == TaskState.RUNNING
            activity.cancel()
            # running cancellation is graceful
            assert activity.status == TaskState.RUNNING
            await activity.done
            assert activity.status == TaskState.CANCELLED
            assert activity.status & TaskState.FINISHED

    @via_usim
    async def test_condition(self):
        async with Scope() as scope:
            activity = scope.do(sleep(20))
            activity_done = activity.done
            assert bool(activity_done) is False
            assert bool(~activity_done) is True
            # waiting for inverted, unfinished activity does not delay
            assert await (~activity_done) is True
            assert time.now == 0
            await (time + 10)
            assert bool(activity_done) is False
            assert bool(~activity_done) is True
            assert await (~activity_done) is True
            assert time.now == 10
            await (time + 10)
            assert bool(activity_done) is True
            assert bool(~activity_done) is False
            assert await activity_done is True
            assert time.now == 20
