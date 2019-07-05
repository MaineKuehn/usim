from typing import TypeVar, Dict, Iterable, Generic, Optional, Callable

from .._core.loop import __LOOP_STATE__
from .tracked import Tracked


T = TypeVar('T')


def _kwarg_validator(name, arguments: Iterable[str]) -> Callable:
    """
    Create a validator for a function taking keyword ``arguments``

    :param name: name to use when reporting a mismatch
    :param arguments: names of arguments the function may receive
    """
    assert arguments
    namespace = {}
    exec("""def %s(*, %s=None):...""" % (
        name,
        '=None, '.join(arguments)
    ), namespace)
    return namespace[name]


class NamedVolume(Dict[str, T]):
    """
    Mapping that supports element-wise operations

    :warning: This is for internal use only.
    """
    def __add__(self, other: 'Dict[str, T]'):
        return self.__class__(
            (key, self[key] + other.get(key, 0))
            for key in self.keys()
        )

    def __sub__(self, other: 'Dict[str, T]'):
        return self.__class__(
            (key, self[key] - other.get(key, 0))
            for key in self.keys()
        )

    def __ge__(self, other: 'Dict[str, T]') -> bool:
        return all(self[key] >= value for key, value in other.items())

    def __gt__(self, other: 'Dict[str, T]') -> bool:
        return all(self[key] > value for key, value in other.items())

    def __le__(self, other: 'Dict[str, T]') -> bool:
        return all(self[key] <= value for key, value in other.items())


class BorrowedResources(Generic[T]):
    def __init__(self, resources: 'BaseResources', amounts: Dict[str, T]):
        self._resources = resources
        self._requested = amounts

    async def __aenter__(self):
        await (self._resources.__available__ >= self._requested)
        await self._resources.__remove_resources__(self._requested)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is GeneratorExit:
            # we are killed forcefully and cannot perform async operations
            # dispatch a new activity to release our resources eventually
            __LOOP_STATE__.LOOP.schedule(
                self._resources.__insert_resources__(self._requested)
            )
        else:
            await self._resources.__insert_resources__(self._requested)


class BaseResources(Generic[T]):
    """
    Internal base class for resource types
    """
    def __init__(self, __zero__: Optional[T] = None, **capacity: T):
        if not capacity:
            raise TypeError(
                '%s requires at least 1 keyword-only argument' % self.__class__.__name__
            )
        __zero__ = __zero__ if __zero__ is not None else\
            type(next(iter(capacity.values())))()  # bare type invocation must be zero
        self._zero = NamedVolume(dict.fromkeys(capacity, __zero__))
        self.__available__ = Tracked(NamedVolume(capacity))
        if not self.__available__ > self._zero:
            raise ValueError('initial capacities must be greater than zero')
        self._verify_arguments = _kwarg_validator('borrow', arguments=capacity.keys())

    async def __insert_resources__(self, amounts: Dict[str, T]):
        new_levels = self.__available__.value + NamedVolume(amounts)
        await self.__available__.set(new_levels)

    async def __remove_resources__(self, amounts: Dict[str, T]):
        new_levels = self.__available__.value - NamedVolume(amounts)
        await self.__available__.set(new_levels)

    def borrow(self, **amounts: T) -> BorrowedResources[T]:
        """
        Temporarily borrow resources for a given context

        :param amounts:
        :return:
        """
        self._verify_arguments(**amounts)
        if not self._zero <= amounts:
            raise ValueError('cannot borrow negative amounts')
        return BorrowedResources(self, amounts)


class Capacity(BaseResources[T]):
    r"""
    Fixed supply of named resources which can be temporarily borrowed

    The resources and their maximum capacity are defined
    when the resource supply is created.
    Afterwards, it is only possible to temporarily :py:meth:`borrow`
    resources:

    .. code:: python3

        # create a limited supply of resources
        resources = Capacity(cores=8, memory=16000)

        # temporarily remove resources
        async with resources.borrow(cores=2, money=4000):
            await computation

    A :py:class:`~.Capacity` guarantees that its resources are conserved and
    cannot be leaked. Once resources are :py:meth:`~.borrow`\ ed, they can
    always be returned promptly.
    """
    def __init__(self, __zero__: Optional[T] = None, **capacity: T):
        super().__init__(__zero__, **capacity)
        self._capacity = NamedVolume(capacity)

    def borrow(self, **amounts: T) -> BorrowedResources[T]:
        borrowing = super().borrow(**amounts)
        if not self._capacity >= amounts:
            raise ValueError('cannot borrow beyond capacity')
        return borrowing


class Resources(BaseResources[T]):
    r"""
    Supply of named resources which can be temporarily borrowed or produced/consumed

    The resources and their initial capacity are defined
    when the resource supply is created.
    Afterwards, the level of resources can be permanently :py:meth:`~.increase`\ d or
    :py:meth:`~.decrease`\ d as well as temporarily decreased by :py:meth:`borrow`\ ing:

    .. code:: python3

        # create an open supply of resources
        resources = Resources(cores=8, memory=4000)

        # increase the resource supply available
        resources.increase(memory=2000)

        # temporarily remove resources
        async with resources.borrow(cores=2, memory=6000):
            await computation

        # decrease the resource supply available
        resources.decrease(cores=4)

    """
    async def set(self, **amounts: T):
        self._verify_arguments(**amounts)
        if not self._zero <= amounts:
            raise ValueError('cannot increase by negative amounts')
        await self.__available__.set(NamedVolume(amounts))

    async def increase(self, **amounts: T):
        self._verify_arguments(**amounts)
        if not self._zero <= amounts:
            raise ValueError('cannot increase by negative amounts')
        await self.__insert_resources__(amounts)

    async def decrease(self, **amounts: T):
        self._verify_arguments(**amounts)
        if not self._zero <= amounts:
            raise ValueError('cannot decrease by negative amounts')
        if not self._zero <= (self.__available__.value - NamedVolume(amounts)):
            raise ValueError('cannot decrease below zero')
        await self.__remove_resources__(amounts)
