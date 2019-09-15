from typing import Type

import pytest

from usim.py.events import Interrupt
from usim.py.resources.resource import Resource, PriorityResource, PreemptiveResource

from .utility import via_usimpy


class TestResource:
    resource_type: Type[Resource] = Resource

    def test_misuse(self, env):
        with pytest.raises(ValueError):
            self.resource_type(env, capacity=0)
        resource = self.resource_type(env, capacity=2)
        with pytest.raises(AttributeError):
            resource.get()
        with pytest.raises(AttributeError):
            resource.put()

    @via_usimpy
    def test_congestion(self, env):
        """Capacity limits concurrently granted requests"""
        resource = self.resource_type(env, capacity=2)

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
        resource = self.resource_type(env, capacity=2)

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
        resource = self.resource_type(env, capacity=1)
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


class TestPriorityResource(TestResource):
    resource_type: Type[Resource] = PriorityResource


class TestPreemptiveResource(TestResource):
    resource_type: Type[Resource] = PreemptiveResource

    @via_usimpy
    def test_preemption(self, env):
        resource = PreemptiveResource(env=env, capacity=1)
        results = []

        def hold_resource(idx: int, duration: float, priority: int):
            while True:
                with resource.request(priority=priority) as claim:
                    try:
                        yield claim
                        yield env.timeout(duration)
                    except Interrupt:
                        continue
                    else:
                        results.append(idx)
                        return

        # launch claims with priority biased towards later laims
        claims = [env.process(hold_resource(idx, 1, 10 - idx)) for idx in range(10)]
        yield claims[0]
        assert results == list(reversed(range(10)))
