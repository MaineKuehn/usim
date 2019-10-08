from typing import Sequence, ClassVar, Type, TypeVar, Generic
from itertools import takewhile

from ..core import Environment
from ..events import Event

__all__ = ['Put', 'Get', 'BaseResource']


# Implementation Note
# We take some liberty in interpreting SimPy's API. Several parts
# are loosely specified - e.g. BaseResource.GetQueue has to satisfy
# different specs for ``BaseResource`` and ``Request``. We take the
# most general if it means the code gets cleaner.


T = TypeVar('T')


class BaseRequest(Event[T]):
    r"""
    Base class for :py:class:`~.Put` and :py:class:`~.Get` events

    A request is commonly created via
    :py:meth:`~.BaseResource.put` or :py:meth:`~.BaseResource.get` and must
    be ``yield``\ ed by a Process to wait until the request has been served.
    If a request has not been served but is no longer desired, the process should
    :py:class:`~.cancel` the request.

    A request can be used as a context manager to automatically cancel it
    at the end of the context. Note that the request is not automatically
    waited on -- this must be done explicitly if desired.

    .. code:: python3

        with resource.get() as request:
            yield request
    """
    def __init__(self, resource: 'BaseResource'):
        super().__init__(resource._env)
        self.resource = resource
        #: the process that requested the action
        self.proc = self.env.active_process

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cancel()

    def cancel(self):
        """
        Cancel the request

        Requests should be cancelled when they have not been triggered but
        are no longer needed. This may happen when a process is interrupted
        while waiting for a request.

        Cancelling is idempotent: If the request has already been triggered or canceled,
        :py:meth:`~.cancel` can still be called without error.
        """
        raise NotImplementedError


class Put(BaseRequest[T]):
    """Request to put content into a resource"""
    def __init__(self, resource: 'BaseResource'):
        super().__init__(resource)
        # Enqueue the event to be processed...
        resource.put_queue.append(self)
        # ...schedule our inverse when we trigger (put item -> get item)...
        self.callbacks.append(resource._trigger_get)
        # ...and immediately check whether we could trigger
        resource._trigger_put(None)

    def cancel(self):
        if not self.triggered:
            self.resource.put_queue.remove(self)


class Get(BaseRequest[T]):
    """Request to get content out of a resource"""
    def __init__(self, resource: 'BaseResource'):
        super().__init__(resource)
        # Enqueue the event to be processed...
        resource.get_queue.append(self)
        # ...schedule our inverse when we trigger (put item -> get item)...
        self.callbacks.append(resource._trigger_put)
        # ...and immediately check whether we could trigger
        resource._trigger_get(None)

    def cancel(self):
        if not self.triggered:
            self.resource.get_queue.remove(self)


class BaseResource(Generic[T]):
    """
    Base class for all synchronised resources of :py:mod:`usim.py`

    This type codifies the basic semantics of :py:mod:`usim.py` resources:
    processes can :py:meth:`~.put` content into the resource or :py:meth:`~.get`
    content out of the resource. Both actions return an
    :py:class:`~usim.py.events.Event`; once the event triggers, the process did
    successfully get or put content into or out of the resource.
    Processes should ``yield`` this even to wait for success of their request.

    .. code:: python3

        def foo(env, resources: BaseResource):
            print('Getting a resource at', env.time)
            yield resources.get()
            print('Got resource at', env.time)
            yield env.timeout(2)
            print('Returning a resource at', env.time)
            yield resources.put()
            print('Returned a resource at', env.time)

    Subclasses should define their behaviour by implementing at least one of:

    :py:attr:`~.BaseResource.PutQueue` or :py:attr:`~.BaseResource.GetQueue`
        The types used to create the :py:attr:`~.put_queue` and :py:attr:`~.get_queue`.
        These may, for example, customize priority of queued requests.

    :py:meth:`~.put` or :py:meth:`~.get`
        The methods used to create :py:class:`~.Put` and :py:class:`~.Get` events.
        These may, for example, customize how much of a resource to handle at once.

    :py:meth:`~._do_put` or :py:meth:`~._do_get`
        The methods used to process :py:class:`~.Put` and :py:class:`~.Get` events.
        These are an alternative to customizing :py:meth:`~.put` or :py:meth:`~.get`.

    .. note::

        This is *not* an Abstract Base Class.
        Subclasses do not need to implement
        :py:meth:`~.BaseResource._do_get` or :py:meth:`~.BaseResource._do_put`.

    .. hint::

        **Migrating to μSim**

        There is no common base type for resources in μSim -- instead there
        are several different types of resources made for various use-cases.
        If you need to create a custom resource, you are free to choose
        whatever interface is appropriate for your use-case.

        μSim itself usually uses the ``await``, ``async for`` and ``async with``
        depending on the intended use of a resource.
        Commonly this means
        ``await resource`` to get content from a resource,
        ``await resource.put(...)`` to add content to a resource,
        ``async for item in resource:`` to subscribe to a resource,
        and
        ``async with resource:`` to temporarily use a resource.
    """
    #: The type used to create :py:attr:`~.put_queue`
    PutQueue: ClassVar[Type[Sequence]] = list
    #: The type used to create :py:attr:`~.get_queue`
    GetQueue: ClassVar[Type[Sequence]] = list

    def __init__(self, env: Environment, capacity):
        self._env = env
        self._capacity = capacity
        #: pending put events
        self.put_queue = self.PutQueue()
        #: pending get events
        self.get_queue = self.GetQueue()

    @property
    def capacity(self):
        """Maximum capacity of the resource"""
        return self._capacity

    def put(self) -> Put[T]:
        """Create a request to put content into the resource"""
        return Put(self)

    def get(self) -> Get[T]:
        """Create a request to get content out of the resource"""
        return Get(self)

    def _trigger_put(self, get_event: Get):
        """
        Trigger all possible put events

        Called when a ``Put`` event was created or a ``Get`` event triggered.
        This trigger scheme handles a new request to an uncontested resource
        (the ``Put`` succeeds immediately),
        as well as a full one (the ``Get`` may serve a waiting ``Put``).

        :param get_event: ``Get`` event that was triggered or :py:const:`None`
        """
        triggered = list(takewhile(self._do_put, self.put_queue))
        self.put_queue = self.put_queue[len(triggered):]

    def _trigger_get(self, put_event: Put):
        """
        Trigger all possible put events

        Called when a ``Get`` event was created or a ``Put`` event triggered.
        This trigger scheme handles a new request to an uncontested resource
        (the ``Get`` succeeds immediately),
        as well as a full one (the ``Put`` may serve a waiting ``Get``).

        :param put_event: ``Get`` event that was triggered or :py:const:`None`
        """
        triggered = list(takewhile(self._do_get, self.get_queue))
        self.get_queue = self.get_queue[len(triggered):]

    # NOTE: Per the SimPy spec, these are **PUBLIC**
    def _do_get(self, get_event: Get) -> bool:
        """
        Trigger a :py:class:`~.Get` event if possible

        :param get_event: the event that may be triggered
        :return: whether another event may be triggered
        """
        raise NotImplementedError("'_do_get' must be overridden in subclasses")

    def _do_put(self, get_event: Put) -> bool:
        """
        Trigger a :py:class:`~.Put` event if possible

        :param get_event: the event that may be triggered
        :return: whether another event may be triggered
        """
        raise NotImplementedError("'_do_put' must be overridden in subclasses")
