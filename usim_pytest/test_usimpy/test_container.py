import pytest

from usim.py.resources.container import Container

from .utility import via_usimpy


class TestContainer:
    def test_misuse(self, env):
        with pytest.raises(ValueError):
            Container(env, capacity=0)
        with pytest.raises(ValueError):
            Container(env, capacity=5, init=20)
        with pytest.raises(ValueError):
            Container(env, capacity=10, init=-5)
        container = Container(env, init=5)
        with pytest.raises(ValueError):
            container.get(0)
        with pytest.raises(ValueError):
            container.put(0)

    @via_usimpy
    def test_get(self, env):
        container = Container(env, init=25)
        yield container.get(5)
        yield container.get(5)
        yield container.get(5)
        yield container.get(5)
        assert env.now == 0
        assert container.level == 5

    @via_usimpy
    def test_put(self, env):
        container = Container(env, init=25)
        yield container.put(5)
        yield container.put(5)
        yield container.put(5)
        yield container.put(5)
        assert env.now == 0
        assert container.level == 45

    @via_usimpy
    def test_get_put(self, env):
        container = Container(env, init=0)
        yield container.put(5)
        yield container.get(5)
        yield container.put(5)
        yield container.put(5)
        yield container.get(5)
        yield container.get(5)
        assert env.now == 0
        assert container.level == 0

    @via_usimpy
    def test_congested(self, env):
        container = Container(env, init=0)

        def producer():
            for _ in range(3):
                yield env.timeout(5)
                yield container.put(10)

        env.process(producer())
        for _ in range(6):
            with container.get(5) as request:
                yield request
        assert env.now == 15

    @via_usimpy
    def test_congested_timeout(self, env):
        container = Container(env, init=0)

        def consumer():
            with container.get(5) as request:
                yield request | env.timeout(10)
                if request.ok:
                    yield env.timeout(5)

        # create more consumers than we can serve
        consumers = [env.process(consumer()) for _ in range(100)]
        yield container.put(20)
        for cons in consumers:
            yield cons
        assert env.now == 10
