import operator
import pytest

from usim import Scope, time
from usim.basics import Tracked

from ..utility import via_usim, assertion_mode


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
comparison_operators = (
    operator.__lt__, operator.__le__,
    operator.__eq__, operator.__ne__,
    operator.__gt__, operator.__ge__,
)


class TestTracked:
    @via_usim
    async def test_representable(self):
        for case in (Tracked(1138), Tracked(1138) > Tracked(1), Tracked(1138) + 1):
            str(case), repr(case)

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

    @via_usim
    async def test_comparison(self):
        value = 1137
        for op in comparison_operators:
            expected = op(value, value)
            expression = op(Tracked(value), value)
            assert expected == bool(expression)
            assert expected != bool(~expression)
            expression = op(value, Tracked(value))
            assert expected == bool(expression)
            assert expected != bool(~expression)
            expression = op(Tracked(value), Tracked(value))
            assert expected == bool(expression)
            assert expected != bool(~expression)

    @via_usim
    async def test_comparison_wait(self):
        value = 1137
        tracked = Tracked(value)
        await (tracked == value)
        assert time.now == 0
        async with Scope() as scope:
            scope.do(tracked + 10, after=10)
            scope.do(tracked + 10, after=20)
            await (tracked == value + 20)
        assert time.now == 20

    @via_usim
    async def test_mutable(self):
        """Tracked does not mutate the initial value if operations are pure"""
        tracked = Tracked([1, 2, 3])
        tracked_value = tracked.value
        await (tracked == [1, 2, 3])
        await (tracked + [4, 5])
        assert tracked_value == [1, 2, 3]
        assert tracked == [1, 2, 3, 4, 5]

    @assertion_mode
    @via_usim
    async def test_tracked_op_tracked(self):
        with pytest.raises(AssertionError):
            Tracked(2) + Tracked(2)
