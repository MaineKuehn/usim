from heapq import heappush, heappop


class WaitQueue:
    def __init__(self):
        self._data = {}
        self._keys = []

    def __bool__(self):
        return bool(self._keys)

    def __len__(self):
        return sum(len(item) for item in self._data.values())

    def update(self, key_items):
        for key, item in key_items:
            self.push(key, item)

    def push(self, key, item):
        try:
            self._data[key].append(item)
        except KeyError:
            self._data[key] = [item]
            heappush(self._keys, key)

    def pop(self):
        key = heappop(self._keys)
        return key, self._data.pop(key)

    def peek(self):
        key = self._keys[0]
        return key, self._data[key]

    def __repr__(self):
        return '[%s]' % ''.join(
            '%s: %s' % (key, self._data[key])
            for key in self._keys
        )