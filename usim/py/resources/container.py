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
    def __init__(self, container, amount):
        if amount <= 0:
            raise ValueError('amount must be greater than 0')
        self.amount = amount
        super(ContainerGet, self).__init__(container)


class Container(BaseResource):
    """
    Resource with ``capacity`` of continuous, indistinguishable content

    A Process may :py:meth:`~.get` out or :py:meth:`~.put` in an arbitrary
    amount of content, provided there is content or ``capacity`` available.
    Requests that cannot be granted immediately are served once sufficient
    content or capacity are available.

    :param capacity: the maximum amount of content available
    :param init: the initial amount of content available

    By default, a :py:class:`~.Container` has infinite capacity but
    starts empty. Note that it is not possible to have a higher initial
    content than maximum capacity.
    """
    def __init__(self, env, capacity=float('inf'), init=0):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        if init < 0:
            raise ValueError("init must be positive")
        if init > capacity:
            raise ValueError("init must not exceed capacity")
        super(Container, self).__init__(env, capacity)
        self._level = init

    @property
    def level(self):
        """The current amount of the content in the container"""
        return self._level

    def put(self, amount=1) -> ContainerPut:
        """Put ``amount`` of content into the container"""
        return ContainerPut(self, amount)

    def get(self, amount=1) -> ContainerGet:
        """Get ``amount`` of content out of the container"""
        return ContainerGet(self, amount)

    def _do_put(self, event):
        if self._capacity - self._level >= event.amount:
            self._level += event.amount
            event.succeed()
            return True

    def _do_get(self, event):
        if self._level >= event.amount:
            self._level -= event.amount
            event.succeed()
            return True
