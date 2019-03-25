import pytest

from usim import Scope, time, eternity, VolatileActivityExit, ActivityState, ActivityCancelled, until, each

from .utility import via_usim


class TestDo:
    """Test bare ``scope.do`` API"""
    @via_usim
    async def test_do(self):
        async def payload():
            return 2

        async with Scope() as scope:
            activity = scope.do(payload())

        assert await activity.result == 2

    @via_usim
    async def test_negative(self):
        async def payload():
            return 2

        async with Scope() as scope:
            _payload = payload()
            with pytest.raises(AssertionError):
                scope.do(_payload, after=-1)
            with pytest.raises(AssertionError):
                scope.do(_payload, at=-1)
        _payload.close()

    @via_usim
    async def test_after(self):
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
    async def test_at(self):
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
    async def test_volatile(self):
        async def payload():
            await eternity
            return 2

        async with Scope() as scope:
            activity = scope.do(payload(), volatile=True)
        with pytest.raises(VolatileActivityExit):
            assert await activity.result
        assert activity.status == ActivityState.FAILED

    @via_usim
    async def test_after_and_at(self):
        async def payload():
            return 2

        async with Scope() as scope:
            _payload = payload()
            with pytest.raises(AssertionError):
                scope.do(_payload, after=1, at=1)
        _payload.close()


class TestNested:
    """Test nested scopes"""
    @via_usim
    async def test_joint_exit(self):
        """Multiple scopes done at the same time"""
        async with Scope() as scope1:
            scope1.do(time + 10)
            async with Scope() as scope2:
                scope2.do(time + 10)
                async with Scope() as scope3:
                    scope3.do(time + 10)
                assert time.now == 10
            assert time.now == 10
        assert time.now == 10

    @via_usim
    async def test_outer_exit(self):
        """Outer scopes done last"""
        async with Scope() as scope1:
            scope1.do(time + 10)
            async with Scope() as scope2:
                scope2.do(time + 7)
                async with Scope() as scope3:
                    scope3.do(time + 5)
                assert time.now == 5
            assert time.now == 7
        assert time.now == 10

    @via_usim
    async def test_inner_exit(self):
        """Inner scopes done last"""
        async with Scope() as scope1:
            scope1.do(time + 5)
            async with Scope() as scope2:
                scope2.do(time + 7)
                async with Scope() as scope3:
                    scope3.do(time + 10)
                assert time.now == 10
            assert time.now == 10
        assert time.now == 10

    @via_usim
    async def test_inner_exit(self):
        """Intermediate scopes done last"""
        async with Scope() as scope1:
            scope1.do(time + 7)
            async with Scope() as scope2:
                scope2.do(time + 10)
                async with Scope() as scope3:
                    scope3.do(time + 5)
                assert time.now == 5
            assert time.now == 10
        assert time.now == 10


@via_usim
async def test_until():
    async def scheduler():
        async with Scope() as scope:
            while True:
                scope.do(run_job())
                await (time + 500)

    async def run_job():
        await (time + 1000)

    async with until(time == 500) as running:
        activity = running.do(scheduler())

    assert time.now == 500
    with pytest.raises(ActivityCancelled):
        await activity.result


@via_usim
@pytest.mark.xfail(raises=ActivityCancelled, strict=True)
async def test_result():
    async def make_job():
        async with Scope() as scope:
            running_job = scope.do(run_job())
            running_job.cancel()
            await running_job.result

    async def run_job():
        await (time + 100)

    async with Scope() as running:
        activity = running.do(make_job())
    await activity


@via_usim
async def test_reuse():
    async def make_job():
        async with Scope() as scope:
            running_job = scope.do(run_job())
            running_job.cancel()
            await running_job

    async def run_job():
        await (time + 100)

    async with until(time == 500) as running:
        activity = running.do(make_job())
    await activity


@via_usim
async def test_order():
    async def add_char(position: int, target: list):
        target.append(chr(ord('a') + position))

    result = []
    async with Scope() as scope:
        for i in range(5):
            scope.do(add_char(i, result))
    assert "".join(result) == "abcde"


@via_usim
async def test_order_with_cancel():
    async def add_char(position: int, target: list):
        target.append(chr(ord('a') + position))

    result = []
    async with Scope() as scope:
        for i in range(7):
            activity = scope.do(add_char(i, result))
            if i % 2 == 0:
                activity.cancel()
    assert "".join(result) == "bdf"


@pytest.mark.timeout(2)
@via_usim
async def test_for_interval():
    expected_time = 0
    async with until(time == 60):
        async for _ in each(interval=5):
            assert time.now == expected_time
            expected_time += 5
    assert time.now == 60
