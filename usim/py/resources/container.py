from .base import BaseResource, Put, Get


class ContainerPut(Put):
    """Request to put ``amount`` of resources into the ``container``"""
    def __init__(self, container: 'Container', amount: float):
        if amount <= 0:
            raise ValueError('amount must be greater than 0')
        self.amount = amount
        super(ContainerPut, self).__init__(container)


class ContainerGet(Get):
    """Request to get ``amount`` of resources out of the ``container``"""
    def __init__(self, container: 'Container', amount: float):
        if amount <= 0:
            raise ValueError('amount must be greater than 0')
        self.amount = amount
        super(ContainerGet, self).__init__(container)


class Container(BaseResource):
    """
    Resource with ``capacity`` of continuous, indistinguishable content

    A Process may :py:meth:`~.get` out or :py:meth:`~.put` in an arbitrary
    amount of content, provided the :py:attr:`~.level` or ``capacity`` suffices.
    Requests that cannot be granted immediately are served once sufficient
    :py:attr:`~.level` or capacity are available.

    :param capacity: the maximum amount of content available
    :param init: the initial :py:attr:`~.level` of content available

    By default, a :py:class:`~.Container` has infinite capacity but
    starts empty. Note that it is not possible to have a higher initial
    content than maximum capacity.

    .. hint::

        **Migrating to μSim**

        The closest equivalent of a :py:class:`~.Container` in μSim
        are :py:class:`~usim.basics.Resources`. Each contains *multiple*
        resource capacities which can be increased, decreased, set, borrowed
        or claimed individually or together.
        To emulate a :py:class:`~.Container`, use :py:class:`~usim.basics.Resources`
        with a single resource type:

        .. code:: python3

            resources = Resources(level=8)
            # put some content into the resource
            await resource.increase(level=8)
            # get some content from the resource
            await resource.decrease(level=8)

        It is always safe to :py:meth:`~usim.basics.Resources.increase`,
        :py:meth:`~usim.basics.Resources.decrease` or
        :py:meth:`~usim.basics.Resources.set` resources -- there is no need to
        cancel requests.
        To avoid leaking resources by not returning them, it is recommended
        to either :py:meth:`~usim.basics.Resources.borrow` or
        :py:meth:`~usim.basics.Resources.claim` resources -- this automatically
        returns the resources at the end of a scope.

        .. code:: python3

            resources = Resources(apples=8, oranges=12)
            # borrow resources when available, returning them automatically
            async with resources.borrow(apples=2) as borrowed:
                print(f'temporarily got {borrowed.levels.apples} apples!')

        When temporarily holding resources, this is represented by yet another
        resources instance. It can be passed around and further divided --
        but is guaranteed never to exceed what was taken from the initial resource.
    """
    def __init__(self, env, capacity: float = float('inf'), init: float = 0):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        if init < 0:
            raise ValueError("init must be positive")
        if init > capacity:
            raise ValueError("init must not exceed capacity")
        super(Container, self).__init__(env, capacity)
        self._level = init

    @property
    def level(self) -> float:
        """The current amount of available content in the container"""
        return self._level

    def put(self, amount=1) -> ContainerPut:
        """Put ``amount`` of content into the container"""
        return ContainerPut(self, amount)

    def get(self, amount=1) -> ContainerGet:
        """Get ``amount`` of content out of the container"""
        return ContainerGet(self, amount)

    def _do_put(self, event: ContainerPut) -> bool:
        if self._capacity - self._level >= event.amount:
            self._level += event.amount
            event.succeed()
            return True
        return False

    def _do_get(self, event: ContainerGet) -> bool:
        if self._level >= event.amount:
            self._level -= event.amount
            event.succeed()
            return True
        return False
