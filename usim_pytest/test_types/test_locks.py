import pytest

from usim import time, Lock, Scope, instant

from ..utility import via_usim


class TestLock:
    @via_usim
    async def test_misuse(self):
        with pytest.raises(AttributeError):
            with Lock():
                ...

    @via_usim
    async def test_acquire_single(self):
        lock = Lock()
        async with lock:
            await (time + 5)
        assert time == 5

    @via_usim
    async def test_acquire_reentry(self):
        lock = Lock()
        async with lock:
            async with lock:
                async with lock:
                    await (time + 5)
        async with lock, lock, lock:
            await (time + 5)
        assert time == 10

    @via_usim
    async def test_acquire_multiple(self):
        lock_a, lock_b, lock_c = Lock(), Lock(), Lock()
        async with lock_a:
            async with lock_b:
                async with lock_c:
                    await (time + 5)
        async with lock_a, lock_b, lock_c:
            await (time + 5)
        assert time == 10

    @via_usim
    async def test_contended(self):
        lock = Lock()

        async def mutext_sleep(delay):
            async with lock:
                await (time + delay)
        async with Scope() as scope:
            scope.do(mutext_sleep(5))
            scope.do(mutext_sleep(5))
            scope.do(mutext_sleep(10))
        assert time == 20

    @via_usim
    async def test_available(self):
        lock = Lock()

        async def hold_lock():
            async with lock:
                await (time + 10)
        assert lock.available
        async with lock:
            assert lock.available
        async with Scope() as scope:
            scope.do(hold_lock())
            await (time + 5)
            assert not lock.available
        assert lock.available

    @via_usim
    async def test_release_exception(self):
        lock = Lock()

        with pytest.raises(KeyError):
            async with lock:
                raise KeyError
        with pytest.raises(KeyError):
            async with lock:
                raise KeyError
        async with lock:  # lock must remain acquirable after exception
            assert True

    @via_usim
    async def test_contested_cancel(self):
        lock = Lock()

        async def hold_lock(duration=10):
            async with lock:
                await (time + duration)

        async with Scope() as scope:
            scope.do(hold_lock())
            middle = scope.do(hold_lock())
            scope.do(hold_lock())
            await (time + 5)
            middle.cancel()
        assert time == 20

    @via_usim
    async def test_designated_cancel(self):
        lock = Lock()
        markers = []

        async def hold_lock(mark, duration=10):
            async with lock:
                await (time + duration)
                markers.append(mark)

        async with Scope() as scope:
            # acquire the lock so children have to queue
            async with lock:
                # target is scheduled to get the lock once we release it...
                target = scope.do(hold_lock(0))
                # ..and then release it for its kin...
                scope.do(hold_lock(1))
                await instant
                # ..but we schedule target to cancel first
                target.cancel()
        # target (mark 0) did not insert itself
        # peer (mark 1) did insert itself after acquiring the lock
        assert markers == [1]
