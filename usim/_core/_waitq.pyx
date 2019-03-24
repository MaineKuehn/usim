# cython: language_level=3
from heapq import heappush, heappop
from collections import deque


cdef class CyWaitQueue:
    cdef dict _data
    cdef list _keys

    def __init__(self):
        self._data = {}
        self._keys = []

    def __bool__(self):
        return bool(self._keys)

    def __len__(self):
        return sum(len(item) for item in self._data.values())

    cpdef push(self, key, item):
        try:
            self._data[key].append(item)
        except KeyError:
            self._data[key] = elements = deque()
            elements.append(item)
            heappush(self._keys, key)

    cpdef pop(self):
        key = heappop(self._keys)
        return key, self._data.pop(key)

    def __repr__(self):
        return '[%s]' % ''.join(
            '%s: %s' % (key, self._data[key])
            for key in self._keys
        )
