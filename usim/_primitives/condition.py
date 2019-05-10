from contextlib import ExitStack

from typing import Coroutine, Generator, Any as AnyT

from .._core.loop import Hibernate, Interrupt as CoreInterrupt

from .notification import Notification, postpone
from .._core.loop import __LOOP_STATE__


class Condition(Notification):
    """
    An asynchronous logical condition

    Every :py:class:`~.Condition` can be used both in an
    asynchronous *and* boolean context.
    In an asynchronous context,
    such as ``await``,
    a :py:class:`~.Condition` triggers when the :py:class:`~.Condition`
    becomes :py:const:`True`.
    In a boolean context,
    such as ``if``,
    a :py:class:`~.Condition` provides its current boolean value.

    .. code:: python

        if condition:    # resume with current value
            print(condition, 'is met')
        else:
            print(condition, 'is not met')

        await condition  # resume when condition is True

        async with until(condition):  # interrupt when condition is True
            ...

    Every :py:class:`~.Condition` supports the bitwise operators
    ``~a`` (not),
    ``a & b`` (and), as well as
    ``a | b`` (or)
    to derive a new :py:class:`~.Condition`.
    While it is possible to use the boolean operators
    ``not``, ``and``, as well as ``or``,
    they immediately evaluate any :py:class:`~.Condition` in a boolean context.

    .. code:: python

        await (a & b)   # resume when both a and b are True
        await (a | b)   # resume when one of a or b are True
        await (a & ~b)  # resume when a is True and b is False

        c = a & b  # derive new Condition...
        await c    # that can be awaited

        d = a and b  # force boolean evaluation
    """
    __slots__ = ()

    def __bool__(self):
        raise NotImplementedError("Condition must implement '__bool__'")

    def __await__(self) -> Generator[AnyT, None, bool]:
        if self:
            yield from postpone().__await__()
        while not self:
            yield from super().__await__()
        return True  # noqa: B901

    def __and__(self, other) -> 'Condition':
        if isinstance(other, All):
            return All(self, *other._children)
        return All(self, other)

    def __or__(self, other) -> 'Condition':
        if isinstance(other, Any):
            return Any(self, *other._children)
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

    def __repr__(self):
        return '<%s, bool=%s, waiters=%d>' % (
            self.__class__.__name__, bool(self), len(self._waiting)
        )


class Connective(Condition):
    """Logical connection of sub-conditions"""
    __slots__ = ('_children',)

    def __init__(self, *conditions: Condition):
        super().__init__()
        self._children = conditions

    def __await__(self) -> Generator[AnyT, None, bool]:
        return (yield from self.__await_children__().__await__())  # noqa: B901

    async def __await_children__(self) -> bool:
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
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join(repr(child) for child in self._children)
        )


class All(Connective):
    """
    Logical AND of all sub-conditions

    The expression ``a & b & c`` is equivalent to ``All(a, b, c)``.
    """
    __slots__ = ()

    def __bool__(self):
        return all(self._children)

    def __and__(self, other) -> 'Condition':
        if isinstance(other, All):
            return All(*self._children, *other._children)
        return All(*self._children, other)

    def __invert__(self):
        return Any(*(~child for child in self._children))

    def __str__(self):
        return '(%s)' % ' & '.join(str(child) for child in self._children)


class Any(Connective):
    """
    Logical OR of all sub-conditions

    The expression ``a | b | c`` is equivalent to ``Any(a, b, c)``.
    """
    __slots__ = ()

    def __bool__(self):
        return any(self._children)

    def __or__(self, other) -> 'Condition':
        if isinstance(other, Any):
            return Any(*self._children, *other._children)
        return Any(*self._children, other)

    def __invert__(self):
        return All(*(~child for child in self._children))

    def __str__(self):
        return '(%s)' % ' | '.join(str(child) for child in self._children)
