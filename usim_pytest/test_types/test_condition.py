from usim import Flag

from ..utility import via_usim


class TestChainedCondition:
    @via_usim
    async def test_chain_and(self):
        a, b, c = Flag(), Flag(), Flag()
        assert not a and not b and not c
        and_chain = a & b & c
        assert not and_chain
        assert ~and_chain
        assert await (~and_chain)
        await a.set()
        assert not and_chain
        assert ~and_chain
        assert await (~and_chain)
        await b.set()
        assert not and_chain
        assert ~and_chain
        assert await (~and_chain)
        await c.set()
        assert and_chain
        assert not ~and_chain
        assert await and_chain

    @via_usim
    async def test_chain_or(self):
        a, b, c = Flag(), Flag(), Flag()
        assert not a or not b or not c
        or_chain = a | b | c
        assert not or_chain
        assert ~or_chain
        assert await (~or_chain)
        await a.set()
        assert or_chain
        assert not ~or_chain
        assert await or_chain
        await b.set()
        assert or_chain
        assert not ~or_chain
        assert await or_chain
        await c.set()
        assert or_chain
        assert not ~or_chain
        assert await or_chain

    @via_usim
    async def test_chain_long(self):
        a, b, c, d, e, f = Flag(), Flag(), Flag(), Flag(), Flag(), Flag()
        chain = a & (b & c) & d | (e | f)
        assert not chain
        assert ~chain
        assert await (~chain)
        await d.set()
        assert not chain
        assert ~chain
        assert await (~chain)
        await c.set()
        assert not chain
        assert ~chain
        assert await (~chain)
        await e.set()
        assert chain
        assert not ~chain
        assert await chain

    @via_usim
    async def test_flatten_and(self):
        a, b, c, d, e, f = Flag(), Flag(), Flag(), Flag(), Flag(), Flag()
        lexical_chain = a & b & c & d & e & f
        parenthesised_chain = a & (b & (c & (d & (e & f))))
        pairwise_chain = (a & b) & (c & d) & (e & f)
        assert lexical_chain._children == parenthesised_chain._children
        assert lexical_chain._children == pairwise_chain._children

    @via_usim
    async def test_flatten_or(self):
        a, b, c, d, e, f = Flag(), Flag(), Flag(), Flag(), Flag(), Flag()
        lexical_chain = a | b | c | d | e | f
        parenthesised_chain = a | (b | (c | (d | (e | f))))
        pairwise_chain = (a | b) | (c | d) | (e | f)
        assert lexical_chain._children == parenthesised_chain._children
        assert lexical_chain._children == pairwise_chain._children
