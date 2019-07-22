import pytest
from typing import Type

from usim import time, Scope
from usim.basics import Queue, Channel, StreamClosed
from usim.typing import Stream

from ..utility import via_usim, turnstamp


class Base1to1Stream:
    stream_type = None  # type: Type[Stream]

    @via_usim
    async def test_representable(self):
        case = self.stream_type()
        str(case), repr(case)

    @via_usim
    async def test_close(self):
        stream = self.stream_type()
        await stream.close()
        with pytest.raises(StreamClosed):
            await stream.put(None)
        with pytest.raises(StreamClosed):
            await stream
        start = turnstamp()
        await stream.close()
        end = turnstamp()
        assert end > start

    @via_usim
    async def test_put_get(self):
        stream = self.stream_type()

        async def fill(*values, delay: float = 5):
            for value in values:
                await stream.put(value)
                await (time + delay)
            await stream.close()

        async def read():
            values = []
            try:
                while True:
                    values.append(await stream)
            except StreamClosed:
                return values

        async with Scope() as scope:
            receiver = scope.do(read())
            scope.do(fill(*range(20)))
        assert (await receiver) == list(range(20))

    @via_usim
    async def test_put_stream(self):
        stream = self.stream_type()

        async def fill(*values, delay: float = 5):
            for value in values:
                await stream.put(value)
                await (time + delay)
            await stream.close()

        async def read():
            values = []
            async for value in stream:
                values.append(value)
            return values

        async with Scope() as scope:
            receiver = scope.do(read())
            scope.do(fill(*range(20)))
        assert (await receiver) == list(range(20))


class Test1to1Queue(Base1to1Stream):
    stream_type = Queue


class Test1to1Channel(Base1to1Stream):
    stream_type = Channel
