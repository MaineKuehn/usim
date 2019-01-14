"""
Synchronizing streams that allow consumers to wait for messages from producers

Streams synchronize **adding** and **retrieving** messages
across multiple producers and consumers.
This allows consumers to wait for messages,
and producers to delay messages as required.

Consumers can retrieve individual messages
or iterate over all messages:

.. code:: python

    value = await stream  # consume a single message from the stream

    async for value in stream:  # consume messages until the stream is closed
        ...

Similarly, producers can send individual or several messages at once:

.. code:: python

    await stream.put(value)
    await stream.send(values)

Note that channels exist *exclusively* for message passing,
and do not serve as :py:class:`Notification`\ s.
A channel cannot be used in an ``async with until`` statement.
"""
from collections import deque

from typing import Generic, TypeVar, Dict, List, Coroutine, Awaitable, Union, Deque

from ..core import GetTask, Interrupt as CoreInterrupt
from .notification import postpone, Hibernate, Notification
from .locks import Lock


#: Type of channel content
ST = TypeVar('ST')


class Closed(Exception):
    def __init__(self, stream):
        self.stream = stream
        super().__init__('%r is closed and cannot provide more messages' % stream)


class Channel(Generic[ST]):
    """
    Unbuffered stream that broadcasts every message to all consumers
    """
    @property
    def closed(self):
        return self._closed

    def __init__(self):
        super().__init__()
        self._consumer_buffers = {}  # type: Dict[Union[Coroutine, ChannelStream], List[ST]]
        self._notification = Notification()
        self._closed = False

    async def close(self):
        self._closed = True
        await self._notification.__awake_all__()

    def __await__(self) -> Awaitable[ST]:
        if self._closed:
            raise Closed(self)
        task = await GetTask()
        self._consumer_buffers[task] = buffer = []
        try:
            yield from self._notification.__await__()
        finally:
            self._consumer_buffers.pop(task)
        if not buffer and self._closed:
            raise Closed(self)
        return buffer[0]

    def __aiter__(self):
        return ChannelStream(self)

    async def put(self, item: ST):
        for buffer in self._consumer_buffers.values():
            buffer.append(item)
        await self._notification.__awake_all__()
        await postpone()


class ChannelStream(Generic[ST]):
    def __init__(self, channel: Channel[ST]):
        self._channel = channel
        self._buffer = channel._consumer_buffers[self] = []  # type: List[ST]

    async def __anext__(self) -> ST:
        while not self._buffer:
            if self._channel.closed:
                raise StopAsyncIteration
            await self._channel._notification
        return self._buffer.pop()

    def __aiter__(self):
        return self


class Queue(Generic[ST]):
    """
    Buffered stream that anycasts messages to individual consumers
    """
    @property
    def closed(self):
        return self._closed

    def __init__(self):
        super().__init__()
        self._buffer = deque()  # type: Deque[ST]
        self._notification = Notification()
        self._read_mutex = Lock()
        self._closed = False

    async def close(self):
        self._closed = True
        await self._notification.__awake_all__()

    def __await__(self) -> Awaitable[ST]:
        yield from self._await_message()

    async def _await_message(self):
        async with self._read_mutex:
            try:
                return self._buffer.popleft()
            except IndexError:
                pass
            if self._closed:
                raise Closed(self)
            await self._notification
            if not self._buffer and self._closed:
                raise Closed(self)
            return self._buffer.popleft()

    async def put(self, item: ST):
        self._buffer.append(item)
        await self._notification.__awake_next__()
        await postpone()


class QueueStream(Generic[ST]):
    def __init__(self, queue: Queue[ST]):
        self._queue = queue

    async def __anext__(self) -> ST:
        try:
            return await self._queue
        except Closed:
            raise StopAsyncIteration

    def __aiter__(self):
        return self
