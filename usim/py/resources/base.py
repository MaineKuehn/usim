from typing import Sequence, ClassVar, Type, TypeVar, Generic
from itertools import takewhile

from ..core import Environment
from ..events import Event


# Implementation Note
# We take some liberty in interpreting SimPy's API. Several parts
# are loosely specified - e.g. BaseResource.GetQueue has to satisfy
# different specs for ``BaseResource`` and ``Request``. We take the
# most general if it means the code gets cleaner.


T = TypeVar('T')


class BaseRequest(Event[T]):
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
        raise NotImplementedError


class Put(BaseRequest[T]):
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
    #: The type used to create :py:attr:`~.put_queue`
    PutQueue: ClassVar[Type[Sequence]] = list
    #: The type used to create :py:attr:`~.get_queue`
    GetQueue: ClassVar[Type[Sequence]] = list

    def __init__(self, env: Environment, capacity: T):
        self._env = env
        self._capacity = capacity
        #: outstanding put events
        self.put_queue = self.PutQueue()
        #: outstanding get events
        self.get_queue = self.GetQueue()

    def put(self) -> Put[T]:
        return Put(self)

    def get(self) -> Get[T]:
        return Get(self)

    def _trigger_put(self, get_event):
        """
        Trigger all possible put events

        Called when a ``Put`` event was created or a ``Get`` event triggered.

        :param get_event: ``Get`` event that was triggered or :py:const:`None`
        """
        triggered = list(takewhile(self._do_put, self.put_queue))
        self.put_queue = self.put_queue[len(triggered):]

    def _trigger_get(self, put_event):
        """
        Trigger all possible put events

        Called when a ``Get`` event was created or a ``Put`` event triggered.

        :param put_event: ``Get`` event that was triggered or :py:const:`None`
        """
        triggered = list(takewhile(self._do_get, self.get_queue))
        self.get_queue = self.get_queue[len(triggered):]

    def _do_get(self, get_event):
        raise NotImplementedError

    def _do_put(self, get_event):
        raise NotImplementedError
