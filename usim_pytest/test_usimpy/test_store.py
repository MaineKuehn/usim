from typing import Type

import pytest

from usim.py.resources.store import Store, FilterStore, PriorityStore, PriorityItem

from .utility import via_usimpy


class TestStore:
    resource_type: Type[Store] = Store

    def test_misuse(self, env):
        with pytest.raises(ValueError):
            self.resource_type(env, capacity=0)

    @via_usimpy
    def test_putget(self, env):
        store = self.resource_type(env)
        item = object()
        yield store.put(item)
        assert (yield store.get()) is item

    @via_usimpy
    def test_pingpong(self, env):
        store = self.resource_type(env)
        item = object()
        yield store.put(item)
        yield store.put((yield store.get()))
        yield store.put((yield store.get()))
        yield store.put((yield store.get()))
        yield store.put((yield store.get()))
        yield store.put((yield store.get()))
        yield store.put((yield store.get()))
        assert (yield store.get()) is item

    @via_usimpy
    def test_waitget(self, env):
        store = self.resource_type(env)
        item = object()
        get = store.get()
        yield store.put(item)
        assert (yield get) is item

    @via_usimpy
    def test_waitput(self, env):
        store = self.resource_type(env, capacity=1)
        puts = [store.put(num) for num in range(10)]
        for num in range(10):
            assert len(store.items) == 1
            assert (yield store.get()) == num
        assert len(store.items) == 0
        for put in puts:
            yield put
        assert env.now == 0


class TestFilterStore(TestStore):
    resource_type: Type[Store] = FilterStore

    @via_usimpy
    def test_filtered(self, env):
        store = FilterStore(env)
        request = store.get(lambda val: val == 1)
        yield store.put(0)
        assert not request.triggered
        yield env.timeout(1)
        assert not request.triggered
        yield store.put(1)
        assert (yield request) == 1
        assert (yield store.get()) == 0


class TestPriorityStore(TestStore):
    resource_type: Type[Store] = PriorityStore

    @via_usimpy
    def test_priority(self, env):
        store = PriorityStore(env)
        for item in range(10):
            yield store.put(PriorityItem(100 - item, item))
        for item in reversed(range(10)):
            stored = yield store.get()
            assert stored.item == item

    def test_ordering(self):
        priorities = 0, 12, -16, 1e6
        for prio_a in priorities:
            for prio_b in priorities:
                assert (PriorityItem(prio_a, 3) > PriorityItem(prio_b, 4))\
                    == (prio_a > prio_b)
                assert (PriorityItem(prio_a, 3) < PriorityItem(prio_b, 4))\
                    == (prio_a < prio_b)
                assert (PriorityItem(prio_a, 3) >= PriorityItem(prio_b, 4))\
                    == (prio_a >= prio_b)
                assert (PriorityItem(prio_a, 3) <= PriorityItem(prio_b, 4))\
                    == (prio_a <= prio_b)
                assert (PriorityItem(prio_a, 3) == PriorityItem(prio_b, 4))\
                    == (prio_a == prio_b)
                assert (PriorityItem(prio_a, 3) != PriorityItem(prio_b, 4))\
                    == (prio_a != prio_b)
