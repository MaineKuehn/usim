from typing import Deque, Generic, TypeVar, Tuple, Dict, List
from heapq import heappush, heappop
from collections import deque


K = TypeVar('K')
V = TypeVar('V')


class WaitQueue(Generic[K, V]):
    def __init__(self):
        self._data = {}  # type: Dict[K, Deque[V]]
        self._keys = []  # type: List[K]

    def __bool__(self):
        return bool(self._keys)

    def __len__(self):
        return sum(len(item) for item in self._data.values())

    def push(self, key: K, item: V):
        try:
            self._data[key].append(item)
        except KeyError:
            self._data[key] = deque([item])
            heappush(self._keys, key)

    def pop(self) -> Tuple[K, Deque[V]]:
        key = heappop(self._keys)
        return key, self._data.pop(key)

    def __repr__(self):
        return '[%s]' % ''.join(
            '%s: %s' % (key, self._data[key])
            for key in self._keys
        )
