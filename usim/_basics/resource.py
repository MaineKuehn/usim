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
    """
    Fixed supply of named resources temporarily taken from a resource supply

    :param resources: The resources to borrow from
    :param amounts: resource levels to borrow
    """
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
        if not capacity:  # Note: this should be a type-error not assert for consistency
            raise TypeError(
                '%s requires at least 1 keyword-only argument' % self.__class__.__name__
            )
        __zero__ = __zero__ if __zero__ is not None else\
            type(next(iter(capacity.values())))()  # bare type invocation must be zero
        self._zero = NamedVolume(dict.fromkeys(capacity, __zero__))
        self.__available__ = Tracked(NamedVolume(capacity))
        assert self.__available__ > self._zero,\
            'initial capacities must be greater than zero'
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

        :param amounts: resource levels to borrow
        :return: async context to borrow resources
        """
        self._verify_arguments(**amounts)
        assert self._zero <= amounts,\
            'cannot borrow negative amounts'
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
        assert self._capacity >= amounts,\
            'cannot borrow beyond capacity'
        return borrowing


class Resources(BaseResources[T]):
    r"""
    Supply of named resources which can be temporarily borrowed or produced/consumed

    The resources and their initial levels are defined
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

    A :py:class:`~.Capacity` guarantees that is always possible
    to increase the level of available resources.
    Once resources are :py:meth:`~.borrow`\ ed, they can
    always be returned promptly.
    """
    async def set(self, **amounts: T):
        """
        Set the level of resources

        :param amounts: resource levels to set

        Only levels of resources that are already part of these
        :py:class:`~.Resources` can be set. Levels cannot be set
        below zero. If a resource is not specified, its level remains
        unchanged.
        """
        self._verify_arguments(**amounts)
        assert self._zero <= amounts,\
            'cannot increase by negative amounts'
        new_levels = self.__available__.value.copy()
        new_levels.update(amounts)
        await self.__available__.set(NamedVolume(new_levels))

    async def increase(self, **amounts: T):
        """
        Increase the level of resources

        :param amounts: resource levels to increase

        Only levels of resources that are already part of these
        :py:class:`~.Resources` can be increased. Levels cannot be increased
        by negative amounts. If a resource is not specified, its level remains
        unchanged.
        """
        self._verify_arguments(**amounts)
        assert self._zero <= amounts,\
            'cannot increase by negative amounts'
        await self.__insert_resources__(amounts)

    async def decrease(self, **amounts: T):
        """
        Decrease the level of resources

        :param amounts: resource levels to decrease

        Only levels of resources that are already part of these
        :py:class:`~.Resources` can be decreased. Levels cannot be decreased
        by negative amounts or below zero. If a resource is not specified, its
        level remains unchanged.
        """
        self._verify_arguments(**amounts)
        assert self._zero <= amounts,\
            'cannot decrease by negative amounts'
        assert self._zero <= (self.__available__.value - NamedVolume(amounts)),\
            'cannot decrease below zero'
        await self.__remove_resources__(amounts)
