from usim import Flag

from ..utility import via_usim


class TestFlag:
    @via_usim
    async def test_set(self):
        flag = Flag()
        assert not flag
        await flag.set()
        assert flag
        await flag.set()
        assert flag
        await flag.set(to=False)
        assert not flag
        await flag.set(to=False)
        assert not flag

    @via_usim
    async def test_invert(self):
        flag = Flag()
        i_flag = ~flag
        assert not flag and i_flag
        assert ~flag is i_flag
        assert flag is ~i_flag
        await i_flag.set(to=False)
        assert flag and not i_flag
        assert ~flag is i_flag
        assert flag is ~i_flag
