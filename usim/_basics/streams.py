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
A channel cannot be used in an ``async with until(...):`` statement.
"""
from collections import deque

from typing import Generic, TypeVar, Dict, List, Coroutine, Awaitable, Union, AsyncIterable, AsyncIterator

from .._core.loop import __LOOP_STATE__
from .._primitives.notification import postpone, Notification, NoSubscribers
from .._primitives.locks import Lock


#: Type of channel content
ST = TypeVar('ST')


class StreamClosed(Exception):
    def __init__(self, stream):
        self.stream = stream
        super().__init__('%r is closed and cannot provide more messages' % stream)


class Channel(AsyncIterable, Generic[ST]):
    """
    Unbuffered stream that broadcasts every message to all consumers
    """
    @property
    def closed(self):
        return self._closed

    def __init__(self):
        super().__init__()
        self._consumer_buffers = {}  # type: Dict[Union[Coroutine, ChannelAsyncIterator], List[ST]]
        self._notification = Notification()
        self._closed = False

    async def close(self):
        self._closed = True
        self._notification.__awake_all__()

    def __await__(self) -> Awaitable[ST]:
        if self._closed:
            raise StreamClosed(self)
        activity = __LOOP_STATE__.LOOP.activity
        self._consumer_buffers[activity] = buffer = []  # type: List[ST]
        try:
            yield from self._notification.__await__()
        finally:
            self._consumer_buffers.pop(activity)
        if not buffer and self._closed:
            raise StreamClosed(self)
        return buffer[0]

    def __aiter__(self):
        return ChannelAsyncIterator(self)

    async def put(self, item: ST):
        for buffer in self._consumer_buffers.values():
            buffer.append(item)
        self._notification.__awake_all__()
        await postpone()


class ChannelAsyncIterator(AsyncIterator, Generic[ST]):
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


class Queue(AsyncIterable, Generic[ST]):
    """
    Buffered stream that anycasts messages to individual consumers
    """
    @property
    def closed(self):
        return self._closed

    def __init__(self):
        super().__init__()
        self._buffer = deque()  # type: deque[ST]
        self._notification = Notification()
        # mutex to ensure readers are ordered
        self._read_mutex = Lock()
        self._closed = False

    def close(self):
        self._closed = True
        self._notification.__awake_all__()

    def __await__(self) -> Awaitable[ST]:
        return (yield from self._await_message().__await__())

    async def _await_message(self):
        async with self._read_mutex:
            try:
                return self._buffer.popleft()
            except IndexError:
                pass
            if self._closed:
                raise StreamClosed(self)
            await self._notification
            if not self._buffer and self._closed:
                raise StreamClosed(self)
            return self._buffer.popleft()

    def __aiter__(self):
        return QueueAsyncIterator(self)

    async def put(self, item: ST):
        self._buffer.append(item)
        try:
            self._notification.__awake_next__()
        except NoSubscribers:
            pass
        await postpone()


class QueueAsyncIterator(AsyncIterator, Generic[ST]):
    def __init__(self, queue: Queue[ST]):
        self._queue = queue

    async def __anext__(self) -> ST:
        try:
            return await self._queue
        except StreamClosed:
            raise StopAsyncIteration

    def __aiter__(self):
        return self


Stream = Union[Channel, Queue]
StreamAsyncIterator = Union[ChannelAsyncIterator, QueueAsyncIterator]
