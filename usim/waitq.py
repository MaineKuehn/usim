from heapq import heappush, heappop


class WaitQueue:
    def __init__(self):
        self._data = {}
        self._keys = []

    def __bool__(self):
        return bool(self._keys)

    def push(self, key, *items):
        try:
            self._data[key].extend(items)
        except KeyError:
            self._data[key] = list(items)
            heappush(self._keys, key)

    def pop(self):
        key = heappop(self._keys)
        return key, self._data.pop(key)

    def peek(self):
        key = self._keys[0]
        return key, self._data[key]
