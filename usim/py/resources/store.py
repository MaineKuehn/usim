from typing import TypeVar, List, Callable, NamedTuple, Any

from sortedcontainers import SortedList

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

        To pass items between activities, use a :py:class:`~usim.basics.Queue`.
        Queues store items for later retrieval:

        .. code:: python3

            queue = Queue()
            # put an item into the queue
            await queue.put(1)
            # get an item out of the queue
            item = await queue

        In addition to adding or retrieving individual items, it is possible to
        subscribe to a queue by iteration:

        .. code:: python3

            async for item in queue:
                print(item)

        Even with several subscribers, a :py:class:`~usim.basics.Queue` yields
        every item only once.
    """
    def __init__(self, env, capacity=float('inf')):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        super().__init__(env, capacity)
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


class FilterStoreGet(StoreGet[T]):
    """
    Request to get an ``item`` out of the ``resource`` if it passes ``filter``

    The ``filter`` function is applied to all :py:attr:`~.FilterStore.items` of a store,
    and the first for which ``filter(item)`` returns :py:const:`True` is the result.
    """
    def __init__(self, resource, filter: Callable[[T], bool] = lambda item: True):
        self.filter = filter
        super().__init__(resource)


def accept_any(item: Any) -> bool:
    """Default :py:class:`~.FilterStore` filter to accept any item"""
    return True


class FilterStore(Store[T]):
    """
    Resource with a fixed ``capacity`` of slots for storing arbitrary objects

    Requests to :py:meth:`~.get` items support a ``filter``, which limits
    the objects that satisfy the request. A request may not be satisfied if the
    store contains only items that do not match the request ``filter``.
    Pending requests remain queued until a valid item appears in the store.

    While requests are *served* in first-in-first-out order, they are not
    *granted* in first-in-first-out order if items fail the ``filter`` of
    earlier requests. In addition, a request has to inspect *all* items in the
    store to conclude it cannot be granted. In the worst case, a store with
    ``n`` items and ``m`` request takes ``O(mn)`` to get or put items.
    """
    def __init__(self, env, capacity=float('inf')):
        super().__init__(env, capacity)
        self._items = []

    def get(self, filter: Callable[[T], bool] = accept_any) -> FilterStoreGet[T]:
        """Get an item out of the store that satisfies ``filter``"""
        return FilterStoreGet(self, filter)

    def _do_get(self, event: FilterStoreGet):
        event_filter = event.filter
        try:
            index = next(
                index for index, item
                in enumerate(self._items)
                if event_filter(item)
            )
        except StopIteration:
            return False
        else:
            event.succeed(self._items.pop(index))
            return True


class PriorityItem(NamedTuple):
    """
    Helper to sort an unorderable ``item`` by a ``priority``

    This class implements a total ordering based on ``priority``;
    ``item`` is ignored for comparisons. This allows using an arbitrary
    ``item`` in a :py:class:`~.PriorityStore` with a well-defined ``priority``.

    The original :py:class:`simpy.resources.store.PriorityItem` only properly provides
    ``a < b`` ordering; all other comparisons may compare ``item``. :py:mod:`usim.py`
    provides well-defined total ordering.
    """
    priority: float
    item: Any  # actually a T, but NamedTuple cannot be Generic in Py3.6

    # Note: NamedTuple already makes all comparisons as a tuple,
    # e.g. (self.priority, self.item) < (other.priority, other.item)
    # This is totally *not* the point of this class. We need to define
    # all comparisons methods to hide those from NamedTuple.
    def __lt__(self, other: 'PriorityItem'):
        if not isinstance(other, PriorityItem):
            return NotImplemented
        return self.priority < other.priority

    def __gt__(self, other: 'PriorityItem'):
        if not isinstance(other, PriorityItem):
            return NotImplemented
        return self.priority > other.priority

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def __eq__(self, other):
        if not isinstance(other, PriorityItem):
            return NotImplemented
        return self.priority == other.priority

    def __ne__(self, other):
        return not self == other


class PriorityStore(Store[T]):
    """
    Resource with a fixed ``capacity`` of slots for storing arbitrary objects in order

    The :py:attr:`~.items` of the store are maintained in sorted order, with smaller
    items stored and served first.
    All items in the store must support ``a < b`` comparisons.
    To store unorderable items, use :py:class:`~.PriorityItem`.
    """
    def __init__(self, env, capacity=float('inf')):
        super().__init__(env, capacity)
        self._items = SortedList()

    def _do_put(self, event):
        if len(self._items) < self._capacity:
            self._items.add(event.item)
            event.succeed()
            return True
        return False

    def _do_get(self, event):
        try:
            item = self._items.pop(0)
        except IndexError:
            return False
        else:
            event.succeed(item)
            return True
