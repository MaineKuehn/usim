r"""
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

from typing import Generic, TypeVar, Dict, List, Deque,\
    Union, AsyncIterable, Generator, Any

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
        self._consumer_buffers = {}  \
            # type: Dict[Any, Union[List[ST], Deque[ST]]]
        self._notification = Notification()
        self._closed = False

    async def close(self):
        """
        Prevent putting further messages into the :py:class:`~.Channel`

        Closing a :py:class:`~.Channel` causes subsequent attempts
        to :py:meth:`~.Channel.put` or retrieve items to fail
        with :py:exc:`~.StreamClosed`.

        A :py:class:`~.Channel` can be closed multiple times;
        subsequent closes have no effects other than :term:`postponement`.
        """
        if not self._closed:
            self._closed = True
            self._notification.__awake_all__()
        await postpone()

    def __await__(self) -> Generator[Any, None, ST]:
        if self._closed:
            raise StreamClosed(self)
        sentinel = object()
        self._consumer_buffers[sentinel] = buffer = []  # type: List[ST]
        try:
            yield from self._notification.__await__()
        finally:
            del self._consumer_buffers[sentinel]
        if not buffer and self._closed:
            raise StreamClosed(self)
        return buffer[0]  # noqa: B901

    async def __aiter__(self):
        sentinel = object()
        self._consumer_buffers[sentinel] = buffer = deque()  # type: Deque[ST]
        while True:
            while buffer:
                yield buffer.popleft()
            if self._closed:
                break
            await self._notification
        del self._consumer_buffers[sentinel]

    async def put(self, item: ST):
        r"""
        Put an item into the :py:class:`~.Channel`

        :param item: the item to broadcast
        :raises StreamClosed: if the stream has been :py:meth:`~.close`\ d
        """
        if self._closed:
            raise StreamClosed(self)
        for buffer in self._consumer_buffers.values():
            buffer.append(item)
        self._notification.__awake_all__()
        await postpone()

    def __repr__(self):
        return (
            '<{self.__class__.__name__}, consumers={consumers}, closed={self._closed}>'
        ).format(
            self=self,
            consumers=len(self._consumer_buffers),
        )


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

    async def close(self):
        """
        Prevent putting further messages into the :py:class:`~.Queue`

        Closing a :py:class:`~.Queue` causes subsequent attempts
        to :py:meth:`~.Queue.put` items to fail with :py:exc:`~.StreamClosed`.
        When there are no items in a closed :py:class:`~.Queue`,
        attempts to retrieve items fail with :py:exc:`~.StreamClosed`.
        Items already buffered may still be received.

        A :py:class:`~.Queue` can be closed multiple times;
        subsequent closes have no effects other than :term:`postponement`.
        """
        if not self._closed:
            self._closed = True
            self._notification.__awake_all__()
        await postpone()

    def __await__(self) -> Generator[Any, None, ST]:
        return (yield from self._await_message().__await__())  # noqa: B901

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

    async def __aiter__(self):
        while True:
            try:
                yield await self
            except StreamClosed:
                break

    async def put(self, item: ST):
        r"""
        Put an item into the :py:class:`~.Queue`

        :param item: the item to enqueue
        :raises StreamClosed: if the stream has been :py:meth:`~.close`\ d
        """
        if self._closed:
            raise StreamClosed(self)
        self._buffer.append(item)
        try:
            self._notification.__awake_next__()
        except NoSubscribers:
            pass
        await postpone()

    def __repr__(self):
        return '<{self.__class__.__name__}, buffer={self._buffer}>'.format(
            self=self,
        )


Stream = Union[Channel, Queue]
