from typing import AsyncIterable, Optional, Dict

from .._primitives.notification import Notification, suspend
from .._core.loop import __LOOP_STATE__


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
        self._congested = Notification()
        self._throughput_scale = 1.0
        self._subscriptions: Dict[object, float] = {}

    async def transfer(
            self, total: float, throughput: Optional[float] = None
    ) -> None:
        """
        Wait until some total volume has been transferred

        .. code:: python3

            await network.transfer(total=50e9)

        :param total: absolute volume to transfer before resuming
        :param throughput: maximum throughput
        """
        transferred = 0
        identifier = object()
        throughput = throughput if throughput is not None else self.throughput
        self._add_subscriber(identifier, throughput)
        while transferred < total:
            window_start = __LOOP_STATE__.LOOP.time
            window_throughput = throughput * self._throughput_scale
            with self._congested.__subscription__():
                await suspend(
                    delay=(total - transferred) / window_throughput, until=None,
                )
            window_end = __LOOP_STATE__.LOOP.time
            transferred += (window_end - window_start) * window_throughput
        self._del_subscriber(identifier)

    def _add_subscriber(self, identifier, throughput):
        self._subscriptions[identifier] = throughput
        self._throttle_subscribers()

    def _del_subscriber(self, identifier):
        del self._subscriptions[identifier]
        self._throttle_subscribers()

    def _throttle_subscribers(self):
        desired_throughput = sum(self._subscriptions.values())
        if desired_throughput > self.throughput:
            self._throughput_scale = self.throughput / desired_throughput
            self._congested.__awake_all__()
        elif self._throughput_scale != 1.0:
            self._throughput_scale = 1.0
            self._congested.__awake_all__()

    async def stream(
            self,
            each: float,
            total: float = float('inf'),
            throughput: Optional[float] = None,
    ) -> AsyncIterable:
        """
        Iteratively transfer chunks of some total volume

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
            chunks, remainder = divmod(total, each)
            for _ in range(int(chunks)):
                await self.transfer(total=each, throughput=throughput)
                yield
            await self.transfer(total=remainder, throughput=throughput)
            yield
