import pytest

from usim import time, Scope
from usim.basics import Queue, StreamClosed

from ..utility import via_usim, turnstamp


class TestQueue:
    @via_usim
    async def test_close(self):
        queue = Queue()
        await queue.close()
        with pytest.raises(StreamClosed):
            await queue.put(None)
        with pytest.raises(StreamClosed):
            await queue
        start = turnstamp()
        await queue.close()
        end = turnstamp()
        assert end > start

    @via_usim
    async def test_put_get(self):
        queue = Queue()

        async def fill(*values, delay: float = 5):
            for value in values:
                await queue.put(value)
                await (time + delay)
            await queue.close()

        async def read():
            values = []
            try:
                while True:
                    values.append(await queue)
            except StreamClosed:
                return values

        async with Scope() as scope:
            scope.do(fill(*range(20)))
            receiver = scope.do(read())
        assert (await receiver) == list(range(20))

    @via_usim
    async def test_put_stream(self):
        queue = Queue()

        async def fill(*values, delay: float = 5):
            for value in values:
                await queue.put(value)
                await (time + delay)
            await queue.close()

        async def read():
            values = []
            async for value in queue:
                values.append(value)
            return values

        async with Scope() as scope:
            scope.do(fill(*range(20)))
            receiver = scope.do(read())
        assert (await receiver) == list(range(20))
