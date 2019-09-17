from typing import TypeVar, List

from .base import Get, Put, BaseResource
from collections import deque


T = TypeVar('T', covariant=True)


class StoreGet(Get[T]):
    """Request to get an ``item`` out of the ``resource``"""


class StorePut(Put[T]):
    """Request to put an ``item`` into the ``store``"""
    def __init__(self, store: 'Store', item: T):
        self.item = item
        super().__init__(store)


class Store(BaseResource[T]):
    """
    Resource with a fixed ``capacity`` of slots for storing arbitrary objects

    A process can :py:meth:`~.put` in specific items,
    provided there is enough ``capacity``.
    A process can :py:meth:`~.get` the next available item out of the store,
    provided there are any in the store.
    If the ``capacity`` is reached or if there are no items,
    the respective request is delayed.

    The :py:class:`~.Store` serves objects in first-in-first-out order.

    .. hint::

        **Migrating to μSim**

        To pass items between processes, use a :py:class:`~usim.basics.Queue`.
        Queues store items for later retrieval:

        .. code:: python3

            queue = Queue()
            # put an item into the queue
            await queue.put(1)
            # get an item out of the queue
            item = await queue

        In addition to adding or retrieving individual items, it is possible to
        subscribe to a queue by iteration:

            async for item in queue:
                print(item)

        Even with several subscribers, a :py:class:`~usim.basics.Queue` yields
        every item only once.
    """
    def __init__(self, env, capacity=float('inf')):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        super(Store, self).__init__(env, capacity)
        #: currently available items
        self._items = deque()

    @property
    def items(self) -> List[T]:
        """The currently available items in the store"""
        return list(self._items)

    def get(self) -> StoreGet[T]:
        """Get an item out of the store"""
        return StoreGet(self)

    def put(self, item: T) -> StorePut[T]:
        """Put an ``item`` into the store"""
        return StorePut(self, item)

    def _do_put(self, event: StorePut):
        if len(self._items) < self._capacity:
            self._items.append(event.item)
            event.succeed()
            return True
        return False

    def _do_get(self, event: StoreGet):
        try:
            item = self._items.popleft()
        except IndexError:
            return False
        else:
            event.succeed(item)
            return True
