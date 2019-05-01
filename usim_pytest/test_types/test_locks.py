import pytest

from usim import time, Lock

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

    @via_usim
    async def test_acquire_reentry(self):
        lock = Lock()
        async with lock:
            async with lock:
                async with lock:
                    await (time + 5)
        async with lock, lock, lock:
            await (time + 5)

    @via_usim
    async def test_acquire_multiple(self):
        lock_a, lock_b, lock_c = Lock(), Lock(), Lock()
        async with lock_a:
            async with lock_b:
                async with lock_c:
                    await (time + 5)
        async with lock_a, lock_b, lock_c:
            await (time + 5)
