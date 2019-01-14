from abc import ABCMeta, abstractmethod
from contextlib import AsyncExitStack

from typing import Coroutine

from ..core import Hibernate, Interrupt as CoreInterrupt

from .notification import Broadcast, Notification, postpone


class Condition(Notification, metaclass=ABCMeta):
    """
    A logical condition that triggers when ``True``

    .. code:: python

        await condition  # resume when condition is True

        async with until(condition):  # abort if condition becomes False
            ...
    """
    @abstractmethod
    def __bool__(self):
        ...

    def __await__(self):
        yield from postpone().__await__()
        while not self:
            yield from super().__await__()
        return True

    def __and__(self, other) -> 'Condition':
        return All(self, other)

    def __or__(self, other) -> 'Condition':
        return Any(self, other)

    @abstractmethod
    def __invert__(self) -> 'Condition':
        ...

    async def __subscribe__(self, interrupt: CoreInterrupt, task: Coroutine = None):
        await super().__subscribe__(interrupt, task)
        # we cannot exit early from a context without entering it
        # triggering will interrupt on the next async operation
        if self:
            await self.__trigger__()


class Connective:
    """Logical connection of sub-conditions"""
    def __init__(self, *conditions: Condition):
        super().__init__()
        # unpack similar connections
        # eliminate duplicates
        self._children = tuple(
            set(condition for condition in conditions if not isinstance(condition, self.__class__)) |
            set(condition._children for condition in conditions if isinstance(condition, self.__class__))
        )

    def __await__(self):
        if self:
            return True
        yield from self.__await_children__().__await__()

    async def __await_children__(self):
        while not self:
            with AsyncExitStack() as stack:
                for child in self._children:
                    await stack.enter_async_context(child)
                await Hibernate()  # hibernate until a child condition triggers
        return True

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(repr(child) for child in self._children))


class All(Connective, Condition, Broadcast):
    """Logical AND of all sub-conditions"""
    def __bool__(self):
        return all(self._children)

    def __invert__(self):
        return Any(*(~child for child in self._children))

    def __str__(self):
        return '(%s)' % ' & '.join(str(child) for child in self._children)


class Any(Connective, Condition, Broadcast):
    """Logical OR of all sub-conditions"""
    def __bool__(self):
        return any(self._children)

    def __invert__(self):
        return All(*(~child for child in self._children))

    def __str__(self):
        return '(%s)' % ' | '.join(str(child) for child in self._children)


class Flag(Broadcast, Condition):
    """Explicitly settable condition"""
    def __init__(self):
        super().__init__()
        self._value = False
        self._inverse = InverseFlag(self)

    def __bool__(self):
        return self._value

    def __await__(self):
        while not self._value:
            yield from super().__await__()
        return True

    async def set(self, to: bool = True):
        """Set the boolean value of this condition"""
        if to and not self:
            self._value = to
            await self.__trigger__()
            await postpone()
        elif self and not to:
            self._value = to
            await self._inverse.__trigger__()
            await postpone()


class InverseFlag(Broadcast, Condition):
    def __init__(self, flag: Flag):
        super().__init__()
        self._event = flag

    def __bool__(self):
        return not self._event

    async def set(self, to=True):
        """Set the boolean value of this condition"""
        await self._event.set(not to)

    def __await__(self):
        if not self._event._value:
            return True
        else:
            yield from super().__await__()
