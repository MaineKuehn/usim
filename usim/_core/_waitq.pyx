# cython: language_level=3
from collections import deque

# HeapQ Cython port

# Size is constant after first insert, so index checking is a waste
# we may be faster using PySequence_Fast_ITEMS
cdef _heappush(heap: list, newitem: object):
    """Push item onto heap, maintaining the heap invariant."""
    cdef Py_ssize_t position = len(heap)
    heap.append(newitem)
    while position > 0:
        parentpos = (position - 1) >> 1
        parent = heap[parentpos]
        if newitem < parent:
            heap[position] = parent
            position = parentpos
            continue
        break
    heap[position] = newitem


cdef _heappop(heap: list):
    """Pop the smallest item off the heap, maintaining the heap invariant."""
    lastelt = heap.pop()    # raises appropriate IndexError if heap is empty
    if heap:
        returnitem = heap[0]
        heap[0] = lastelt
        position = 0
        _siftup(heap, 0)
        return returnitem
    return lastelt


cdef _siftup(heap: list, tainted_pos: Py_ssize_t):
    endpos = len(heap)
    startpos = tainted_pos
    new_item = heap[tainted_pos]
    # Bubble up the smaller child until hitting a leaf.
    cdef Py_ssize_t child_pos = 2 * tainted_pos + 1    # leftmost child position
    while child_pos < endpos:
        # Set childpos to index of smaller child.
        rightpos = child_pos + 1
        if rightpos < endpos and not heap[child_pos] < heap[rightpos]:
            child_pos = rightpos
        # Move the smaller child up.
        heap[tainted_pos] = heap[child_pos]
        tainted_pos = child_pos
        child_pos = 2 * tainted_pos + 1
    # The leaf at tainted_pos is empty now.  Put new_item there, and bubble it up
    # to its final resting place (by sifting its parents down).
    heap[tainted_pos] = new_item
    _siftdown(heap, startpos, tainted_pos)


cdef _siftdown(heap: list, startpos: Py_ssize_t, pos: Py_ssize_t):
    newitem = heap[pos]
    # Follow the path to the root, moving parents down until finding a place
    # newitem fits.
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if newitem < parent:
            heap[pos] = parent
            pos = parentpos
            continue
        break
    heap[pos] = newitem


cdef class CyWaitQueue:
    cdef dict _data
    cdef list _keys

    def __init__(self):
        self._data = {}
        self._keys = []

    def __bool__(self):
        return bool(self._keys)

    def __len__(self):
        cdef Py_ssize_t length = 0
        for item in self._data.values():
            length += len(item)
        return length

    cpdef push(self, key, item):
        try:
            self._data[key].append(item)
        except KeyError:
            self._data[key] = elements = deque()
            elements.append(item)
            _heappush(self._keys, key)

    cpdef pop(self):
        key = _heappop(self._keys)
        return key, self._data.pop(key)

    def __repr__(self):
        return '<CyWaitQueue [%s]>' % ''.join(
            '%s: %s' % (key, self._data[key])
            for key in self._keys
        )
