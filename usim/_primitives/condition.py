from contextlib import ExitStack

from typing import Coroutine, Awaitable

from .._core.loop import Hibernate, Interrupt as CoreInterrupt

from .notification import Notification, postpone
from .._core.loop import __LOOP_STATE__


class Condition(Notification):
    """
    A logical condition that triggers when ``True``

    .. code:: python

        await condition  # resume when condition is True

        async with until(condition):  # abort if condition becomes False
            ...
    """
    __slots__ = ()

    def __bool__(self):
        raise NotImplementedError("Condition must implement '__bool__'")

    def __await__(self) -> Awaitable[bool]:
        if self:
            yield from postpone().__await__()
        while not self:
            yield from super().__await__()
        return True

    def __and__(self, other) -> 'Condition':
        return All(self, other)

    def __or__(self, other) -> 'Condition':
        return Any(self, other)

    def __invert__(self) -> 'Condition':
        raise NotImplementedError("Condition must implement '__invert__'")

    def __trigger__(self):
        """Trigger the condition, waking up waiting tasks"""
        self.__awake_all__()

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        # we cannot exit early from a context without entering it
        # triggering will interrupt on the next async operation
        if self:
            interrupt.scheduled = True
            __LOOP_STATE__.LOOP.schedule(waiter, signal=interrupt)
        else:
            super().__subscribe__(waiter, interrupt)


class Connective(Condition):
    """Logical connection of sub-conditions"""
    __slots__ = ('_children',)

    def __init__(self, *conditions: Condition):
        super().__init__()
        # unpack similar connections
        # eliminate duplicates
        self._children = tuple(
            set(condition for condition in conditions if not isinstance(condition, self.__class__)) |
            set(condition._children for condition in conditions if isinstance(condition, self.__class__))
        )

    def __await__(self):
        yield from self.__await_children__().__await__()

    async def __await_children__(self):
        await postpone()
        while not self:
            with ExitStack() as stack:
                for child in self._children:
                    # we only need to wait for children which
                    # are not True yet
                    if child:
                        continue
                    stack.enter_context(child.__subscription__())
                await Hibernate()  # hibernate until a child condition triggers
        return True

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(repr(child) for child in self._children))


class All(Connective):
    """Logical AND of all sub-conditions"""
    __slots__ = ()

    def __bool__(self):
        return all(self._children)

    def __invert__(self):
        return Any(*(~child for child in self._children))

    def __str__(self):
        return '(%s)' % ' & '.join(str(child) for child in self._children)


class Any(Connective):
    """Logical OR of all sub-conditions"""
    __slots__ = ()

    def __bool__(self):
        return any(self._children)

    def __invert__(self):
        return All(*(~child for child in self._children))

    def __str__(self):
        return '(%s)' % ' | '.join(str(child) for child in self._children)
