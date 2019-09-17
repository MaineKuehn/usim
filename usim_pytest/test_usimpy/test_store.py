from typing import Type

import pytest

from usim.py.resources.store import Store

from .utility import via_usimpy


class TestStore:
    resource_type: Type[Store] = Store

    def test_misuse(self, env):
        with pytest.raises(ValueError):
            Store(env, capacity=0)

    @via_usimpy
    def test_putget(self, env):
        store = Store(env)
        item = object()
        yield store.put(item)
        assert (yield store.get()) is item

    @via_usimpy
    def test_pingpong(self, env):
        store = Store(env)
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
        store = Store(env)
        item = object()
        get = store.get()
        yield store.put(item)
        assert (yield get) is item

    @via_usimpy
    def test_waitput(self, env):
        store = Store(env, capacity=1)
        puts = [store.put(num) for num in range(10)]
        for num in range(10):
            assert len(store.items) == 1
            assert (yield store.get()) == num
        assert len(store.items) == 0
        for put in puts:
            yield put
        assert env.now == 0