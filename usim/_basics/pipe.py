from typing import AsyncIterable, Optional, NamedTuple, List, Dict

from .._primitives.flag import Flag


class Transfer(NamedTuple):
    total: float
    throughput: float
    transferred: List[float]


class Pipe:
    """
    .. code:: python3

        network = Pipe(throughput=100)

        async with network.block(throughput=50):
            await network.transfer(10000, throughput=100)
    """
    def __init__(self, throughput: float):
        assert throughput > 0
        self.throughput = throughput
        self._subscribed: Dict[Flag, Transfer] = {}

    async def transfer(
            self, total: float, throughput: Optional[float] = None
    ):
        """
        Wait until some total volume has been transferred

        .. code:: python3

            await network.transfer(total=50e9)

        :param total: absolute volume to transfer before resuming
        :param throughput: maximum throughput at
        :return:
        """
        notification = Flag()
        await notification

    async def stream(
            self,
            each: float,
            total: float = float('inf'),
            throughput: Optional[float] = None,
    ) -> AsyncIterable:
        """
        Wait between transferring chunks of some total volume

        .. code:: python3

            async for _ in network.stream(each=10e3, total=50e9):
                ...

        :param each:
        :param total:
        :param throughput:
        :return:
        """
        if total == float('inf'):
            while True:
                await self.transfer(total=each, throughput=throughput)
                yield
        else:
            progress = 0
            while progress < total:
                progress += await self.transfer(
                    total=min(each, total - progress), throughput=throughput
                )
                yield
