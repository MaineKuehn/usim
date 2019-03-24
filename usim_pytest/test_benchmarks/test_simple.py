import pytest

from usim_pytest.utility import via_usim

from usim import Scope


@via_usim
@pytest.mark.benchmark
async def test_usim(benchmark):
    async def payload():
        return 2

    @benchmark
    async def result():
        async with Scope() as scope:
            activity = scope.do(payload())
        return await activity.result

    assert result == 2
