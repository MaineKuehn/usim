import operator
import pytest

from usim.basics import Tracked

from ..utility import via_usim


modifying_operators = (
    operator.__add__, operator.__sub__,
    operator.__mul__, operator.__matmul__, operator.__truediv__, operator.__floordiv__,
    operator.__mod__, operator.__pow__, operator.__lshift__, operator.__rshift__,
    operator.__and__, operator.__or__, operator.__xor__,
)


class TestTracked:
    @via_usim
    async def test_operators(self):
        for op in modifying_operators:
            tracked = Tracked(1137)
            try:
                expected = op(tracked.value, 10)
            except TypeError:
                with pytest.raises(TypeError):
                    await op(tracked, 10)
            else:
                result = await op(tracked, 10)
                assert expected == result
