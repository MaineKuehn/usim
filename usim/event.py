from abc import ABCMeta, abstractmethod

from .core import Hibernate, Interrupt, GetTask, Schedule


class Event(object, metaclass=ABCMeta):
    def __init__(self):
        self._waiting = []

    @abstractmethod
    def __bool__(self):
        raise NotImplementedError('Event subtypes must implement bool(event)')

    def __await__(self):
        """Await that this Event is set"""
        if self:
            return
        # unset - store THIS STACK for resumption
        stack = yield from GetTask().__await__()
        self._waiting.append(stack)
        try:
            yield Hibernate().__await__()  # break point - we are resumed when the event is set
        except Interrupt:
            self._waiting.remove(stack)
            raise

    def __del__(self):
        if not self and self._waiting:
            raise RuntimeError('%r collected without releasing %d waiting tasks' % (self, len(self._waiting)))

    async def _release_waiting(self):
        for waiter in self._waiting:
            await Schedule(waiter)
        self._waiting.clear()

    def __repr__(self):
        return '<%s, set=%s, waiters=%d>' % (self.__class__.__name__, bool(self), len(self._waiting))
