import pytest

from usim.py.resources.resource import Resource

from .utility import via_usimpy


class TestResource:
    def test_misuse(self, env):
        with pytest.raises(ValueError):
            Resource(env, capacity=0)
        resource = Resource(env, capacity=2)
        with pytest.raises(AttributeError):
            resource.get()
        with pytest.raises(AttributeError):
            resource.put()

    @via_usimpy
    def test_congestion(self, env):
        """Capacity limits concurrently granted requests"""
        resource = Resource(env, capacity=2)

        def hold_resource(duration: float):
            claim = resource.request()
            yield claim
            yield env.timeout(duration)
            yield resource.release(claim)

        # 10 claims, 2 concurrent => 5 consecutive claiming pairs
        claims = [env.process(hold_resource(1)) for _ in range(10)]
        yield claims[-1]
        assert env.now == 5

    @via_usimpy
    def test_scope_release(self, env):
        """`with request:` releases claim automatically"""
        resource = Resource(env, capacity=2)

        def hold_resource(duration: float):
            with resource.request() as request:
                yield request
                yield env.timeout(duration)

        def touch_resource():
            with resource.request():
                yield env.timeout(0)

        # 10 claims, 2 concurrent => 5 consecutive claiming pairs
        claims = [env.process(touch_resource()) for _ in range(10)]\
            + [env.process(hold_resource(1)) for _ in range(10)]
        yield claims[-1]
        assert env.now == 5

    @via_usimpy
    def test_release_idemptotent(self, env):
        """Requests can be released multiple times"""
        resource = Resource(env, capacity=1)
        claim = resource.request()
        yield claim
        assert resource.count == 1
        yield resource.release(claim)
        assert resource.count == 0
        yield resource.release(claim)
        yield resource.release(claim)
        yield resource.release(claim)
        yield resource.release(claim)
        assert resource.count == 0
        assert env.now == 0
