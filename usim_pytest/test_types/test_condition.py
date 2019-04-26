from usim import Scope, Flag

from ..utility import via_usim


class TestCondition:
    @via_usim
    async def test_chain_and(self):
        a, b, c = Flag(), Flag(), Flag()
        assert not a and not b and not c
        and_chain = a & b & c
        assert not and_chain
        async with Scope() as scope:
            wait_chain = scope.do(and_chain)
            await a.set()
            assert not and_chain
            await b.set()
            assert not and_chain
            await c.set()
            assert and_chain
            await wait_chain

    @via_usim
    async def test_chain_or(self):
        a, b, c = Flag(), Flag(), Flag()
        assert not a or not b or not c
        or_chain = a | b | c
        assert not or_chain
        async with Scope() as scope:
            wait_chain = scope.do(or_chain)
            await a.set()
            assert or_chain
            await b.set()
            assert or_chain
            await c.set()
            assert or_chain
            await wait_chain
