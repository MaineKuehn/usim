from usim.py.resources.resource import Resource

from .utility import via_usimpy


class TestResource:
    @via_usimpy
    def test_congestion(self, env):
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
