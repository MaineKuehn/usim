from typing import List
from ..core import Environment
from .base import Put, Get, BaseResource


class Request(Put):
    """
    Request usage of a ``resource``

    This event is triggered once the request has been granted by the resource.
    If the resource has sufficient capacity, the request is granted immediately.
    Otherwise, the request is delayed until another request is released.

    A request should always be either cancelled before being granted
    or released after being granted.
    A request can be used in a :keyword:`with` statement to automatically
    cancel or release it as appropriate at the end of the context.
    Note that success of the usage request is not automatically
    waited on -- this must be done explicitly if desired.

    .. code:: python3

        with resource.request() as request:
            yield request
        # request is no longer held here
    """
    #: undocumented, set by Resource._do_get
    __slots__ = 'usage_since',

    def __exit__(self, exc_type, value, traceback):
        if self.triggered:
            self.resource.release(self)
        super().__exit__(exc_type, value, traceback)


class Release(Get):
    """
    Release a previous ``request`` of a ``resource``
    """
    __slots__ = 'request',

    def __init__(self, resource, request):
        self.request = request
        super(Release, self).__init__(resource)


class Resource(BaseResource):
    def __init__(self, env: Environment, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        super().__init__(env, capacity)
        #: All :py:class:`~.Request`\ s currently granted for the resource.
        self.users = []  # type: List[Request]

    @property
    def queue(self) -> List[Request]:
        r"""Pending :py:class:`~.Request`\ s currently waiting for the resource."""
        return self.put_queue

    @property
    def count(self) -> int:
        r"""Number of :py:class:`~.Request`\ s currently granted for the resource."""
        return len(self.users)

    # These do *not* raise a well-defined error in SimPy,
    # but instead fail with a follow-up AttributeError.
    # We raise said error *now* to have a better help message.
    def put(self):
        raise AttributeError(
            f"cannot put/get {self.__class__.__name__}, use request/release instead"
        )

    def get(self):
        raise AttributeError(
            f"cannot put/get {self.__class__.__name__}, use request/release instead"
        )

    def request(self) -> Request:
        """Request usage of a ``resource``"""
        return Request(self)

    def release(self, request: Request) -> Release:
        """Release a previous usage ``request`` of a ``resource``"""
        return Release(self, request)

    def _do_put(self, event: Request) -> bool:
        if len(self.users) < self._capacity:
            self.users.append(event)
            event.usage_since = self._env.now
            print('trigger', self)
            event.succeed()
            return True
        return False

    def _do_get(self, event: Release) -> bool:
        # releasing a Request should be idempotent
        try:
            self.users.remove(event.request)
        except ValueError:
            pass
        event.succeed()
        # releasing always succeeds
        return True
