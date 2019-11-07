from typing import Optional, Dict

from .._primitives.notification import Notification, suspend
from .._core.loop import __LOOP_STATE__


class Pipe:
    """
    Shared transport for resources with a limited total throughput

    :param throughput: limit of total throughput

    The throughput limit of a pipe is defined when a :py:class:`Pipe`
    is created.
    Afterwards, :term:`activities <activity>` may temporarily request transfers
    through the :py:class:`Pipe` with a maximum throughput.
    If the sum of throughput from all transfers exceeds the throughput limit,
    transfers are throttled accordingly.

    .. code:: python3

        connection = Pipe(throughput=3)

        # transfers below limit
        await connection.transfer(total=10, throughput=2)  # takes 5 time units

        # transfers above limit
        async with Scope() as scope:  # takes 10 time units
            scope.do(connection.transfer(15, throughput=3)
            scope.do(connection.transfer(15, throughput=3)

    """
    def __init__(self, throughput: float):
        assert throughput > 0, 'throughput must be positive'
        self.throughput = throughput
        self._congested = Notification()
        self._throughput_scale = 1.0
        self._subscriptions: Dict[object, float] = {}

    async def transfer(
            self, total: float, throughput: Optional[float] = None
    ) -> None:
        """
        Wait until some total volume has been transferred

        :param total: absolute volume to transfer before resuming
        :param throughput: maximum throughput of transfer

        The effective ``throughput`` is bounded by the transfer's ``throughput``
        as well as the Pipe's :py:attr:`~.throughput` weighted
        by all transfers' ``throughput``. For example, if two transfers each request
        the entire :py:attr:`~.throughput`, each receives only half.

        .. code:: python3

            network = Pipe(throughput=64)
            await network.transfer(total=50 * 1024, throughput=128)  # transfer with 64

        If ``throughput`` is not given, it defaults to the Pipe's
        :py:attr:`~.throughput` limit.
        """
        assert total > 0, 'total must be positive'
        assert throughput is None or throughput > 0,\
            'throughput must be positive or None'
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
