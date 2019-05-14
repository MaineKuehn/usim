import operator
import pytest

from usim.basics import Tracked

from ..utility import via_usim


modifying_operators = (
    operator.__add__, operator.__sub__,
    operator.__mul__, operator.__matmul__,
    operator.__truediv__, operator.__floordiv__,
    operator.__mod__, operator.__pow__, operator.__lshift__, operator.__rshift__,
    operator.__and__, operator.__or__, operator.__xor__,
)
inplace_operators = (
    operator.__iadd__, operator.__isub__,
    operator.__imul__, operator.__imatmul__,
    operator.__itruediv__, operator.__ifloordiv__,
    operator.__imod__, operator.__ipow__, operator.__ilshift__, operator.__irshift__,
    operator.__iand__, operator.__ior__, operator.__ixor__,
)


class TestTracked:
    @via_usim
    async def test_misuse(self):
        tracked = Tracked(1137)
        with pytest.raises(TypeError):
            await tracked
        with pytest.raises(TypeError):
            bool(tracked)

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
                assert result is None
                assert expected == tracked.value

    @via_usim
    async def test_operator_pow(self):
        tracked = Tracked(1137)
        expected = pow(tracked.value, 42)
        result = await pow(tracked, 42)
        assert result is None
        assert expected == tracked.value
        expected = pow(tracked.value, 42, 3)
        result = await pow(tracked, 42, 3)
        assert result is None
        assert expected == tracked.value

    @via_usim
    async def test_reflected(self):
        """Reflected operations are not well-defined"""
        for op in modifying_operators:
            tracked = Tracked(1137)
            with pytest.raises(TypeError):
                await op(10, tracked)

    @via_usim
    async def test_inplace(self):
        """Inplace operations are not well-defined"""
        for op in inplace_operators:
            tracked = Tracked(1137)
            with pytest.raises(TypeError):
                op(tracked, 10)
