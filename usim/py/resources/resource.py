from typing import List, Optional

from sortedcontainers import SortedKeyList

from ..core import Environment
from ..events import Process
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
    r"""
    Resource with a fixed ``capacity`` of usage slots

    A process may :py:meth:`request` a single usage slot, which is granted
    as soon as it becomes available. When all slots are taken, each further
    :py:meth:`request` is queued until a previous request is :py:meth:`release`\ d.

    .. warning::

        Both :py:meth:`~.put` and :py:meth:`~.get` cannot be used on this resource type.
    """
    def __init__(self, env: Environment, capacity: int = 1):
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
        """Not supported, use :py:meth:`~.request` instead"""
        raise AttributeError(
            f"cannot put/get {self.__class__.__name__}, use request/release instead"
        )

    def get(self):
        """Not supported, use :py:meth:`~.release` instead"""
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


class PriorityRequest(Request):
    r"""
    Request usage of a ``resource`` with a given ``priority``

    :param priority: order of this request; smaller is chosen first
    :param preempt: whether to replace a request that has worse priority
                    if the ``resource`` is congested

    By default, the ordering of priority of requests is determined by their
    ``priority``, then creation ``time``, then whether they ``preempt``.
    Requests with smaller values and ``preempt=True`` are chosen first.
    """
    def __init__(self, resource, priority: float = 0, preempt=True):
        #: priority of this request, lower is chosen first
        self.priority = priority
        self.preempt = preempt
        #: time at which the request was made
        self.time = resource._env.now
        #: time at which the request was granted
        self.usage_since = None  # type: Optional[float]
        #: sort key of this resource - requests with smaller key are chosen first
        self.key = (self.priority, self.time, not self.preempt)
        super(PriorityRequest, self).__init__(resource)


class SortedQueue(SortedKeyList):
    def __init__(self, maxlen=None):
        if maxlen is not None:
            raise NotImplementedError(
                "'SortedQueue.maxlen' is not implemented "
                "by the μSim compatibility layer"
            )
        super().__init__(key=lambda p_request: p_request.key)

    # SortedKeyList does not support the "insert at <position>" methods
    # of list - because positions are meaningless when items are sorted.
    #
    # The SimPy Resource API uses 'append' to mean 'push' so we provide
    # the correct operation with the expected name.
    def append(self, value):
        self.add(value)


class PriorityResource(Resource):
    r"""
    Resource with a fixed ``capacity`` of usage slots granted with priorities

    A process may :py:meth:`request` a single usage slot, which is granted
    as soon as it becomes available. When all slots are taken, each further
    :py:meth:`request` is queued until a previous request is :py:meth:`release`\ d
    and no request of better priority is queued.
    """
    PutQueue = SortedQueue

    def request(self, priority=0) -> PriorityRequest:
        """Request usage of a ``resource`` with a given ``priority``"""
        return PriorityRequest(self, priority)


class Preempted(object):
    """
    Information on a preemption, carried as the cause of an Interrupt

    A process which did successfully :py:meth:`~.PreemptiveResource.request` a resource
    may be preempted by a request of better priority.
    The initial process then receives a :py:class:`~.Interrupt`, whose
    :py:attr:`~.Interrupt.cause` is an instance of this class.
    """
    __slots__ = 'by', 'usage_since', 'resource'

    def __init__(self, by: Process, usage_since: float, resource: 'PreemptiveResource'):
        #: process that triggered the preemption
        self.by = by
        #: time since when the resource was used
        self.usage_since = usage_since
        #: the resource that was lost
        self.resource = resource


class PreemptiveResource(PriorityResource):
    r"""
    Resource with a fixed ``capacity`` of usage slots preempted with priorities

    A process may :py:meth:`request` a single usage slot, which is granted
    as soon as it becomes available. When all slots are taken, each further
    :py:meth:`request` may preempt already granted :py:meth:`request`\ s of
    worse priority. Otherwise, the request  is queued until a previous request
    is :py:meth:`release`\ d and no request of better priority is queued.
    """
    def __init__(self, env: Environment, capacity: int):
        super().__init__(env, capacity)
        #: All :py:class:`~.Request`\ s currently granted for the resource.
        self.users = SortedQueue()  # type: SortedQueue[PriorityRequest]

    def _do_put(self, event: PriorityRequest):
        # Check if we can preempt the least-priority process
        if len(self.users) >= self.capacity and event.preempt:
            preempt_candidate = self.users[-1]
            if event.key < preempt_candidate.key:
                self.users.remove(preempt_candidate)
                preempt_candidate.proc.interrupt(
                    Preempted(
                        by=event.proc,
                        usage_since=preempt_candidate.usage_since,
                        resource=self
                    ))
        return super(PreemptiveResource, self)._do_put(event)
