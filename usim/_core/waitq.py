import os
from typing import Generic, TypeVar, Tuple, Dict, List, Union, Type
from heapq import heappush, heappop
from collections import deque

from sortedcontainers import SortedDict


K = TypeVar('K')
V = TypeVar('V')


class HQWaitQueue(Generic[K, V]):
    __slots__ = ('_data', '_keys')

    def __init__(self):
        self._data = {}  # type: Dict[K, deque[V]]
        self._keys = []  # type: List[K]

    def __bool__(self):
        return bool(self._keys)

    def __len__(self):
        return sum(len(item) for item in self._data.values())

    def push(self, key: K, item: V):
        try:
            self._data[key].append(item)
        except KeyError:
            self._data[key] = elements = deque()  # type: deque[V]
            elements.append(item)
            heappush(self._keys, key)

    def pop(self) -> 'Tuple[K, deque[V]]':
        key = heappop(self._keys)
        return key, self._data.pop(key)

    def __repr__(self):
        return '<HQWaitQueue [%s]>' % ''.join(
            '%s: %s' % (key, self._data[key])
            for key in self._keys
        )


class SDWaitQueue(Generic[K, V]):
    __slots__ = ('_data',)

    def __init__(self):
        self._data = SortedDict()  # type: SortedDict[K, deque[V]]

    def __bool__(self):
        return bool(self._data)

    def __len__(self):
        return sum(len(item) for item in self._data.values())

    def push(self, key: K, item: V):
        try:
            self._data[key].append(item)
        except KeyError:
            self._data[key] = elements = deque()  # type: deque[V]
            elements.append(item)

    def pop(self) -> 'Tuple[K, deque[V]]':
        return self._data.popitem(0)

    def __repr__(self):
        return '<SDWaitQueue [%s]>' % ''.join(
            '%s: %s' % (key, value)
            for key, value in self._data.items()
        )


QUEUETYPE_KEY = 'USIM_WAITQUEUE'
if os.environ.get(QUEUETYPE_KEY, '').upper() == 'SD':
    WaitQueue = SDWaitQueue  # type: Union[Type[SDWaitQueue], Type[HQWaitQueue]]
elif os.environ.get(QUEUETYPE_KEY, '').upper() == '':
    WaitQueue = HQWaitQueue
else:
    raise EnvironmentError(
        'Invalid %r: %r' % (QUEUETYPE_KEY, os.environ.get(QUEUETYPE_KEY))
    )
