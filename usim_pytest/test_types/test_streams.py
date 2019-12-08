import pytest
from typing import Type

from usim import time, Scope
from usim import Queue, Channel, StreamClosed
from usim.typing import Stream

from ..utility import via_usim, assert_postpone


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
        assert stream.closed
        with pytest.raises(StreamClosed):
            await stream.put(None)
        with pytest.raises(StreamClosed):
            await stream
        # closing is idempotent
        with assert_postpone():
            await stream.close()
        assert stream.closed

    @via_usim
    async def test_put_get(self):
        """``Stream.put`` interlocked with ``await Stream``"""
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
        """``Stream.put`` interlocked with ``async for ... in Stream``"""
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

    # Only applies to Queue since Channel does not buffer items
    @via_usim
    async def test_full_get(self):
        """``await Queue`` on filled queue"""
        stream = self.stream_type()

        for val in range(20):
            await stream.put(val)
        await stream.close()
        for val in range(20):
            with assert_postpone():
                fetched = await stream
                assert fetched == val


class Test1to1Channel(Base1to1Stream):
    stream_type = Channel
