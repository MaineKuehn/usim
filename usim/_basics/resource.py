from typing import TypeVar, Generic, Optional, Type

from .._core.loop import __LOOP_STATE__
from ._resource_level import __specialise__, ResourceLevels
from .tracked import Tracked


T = TypeVar('T')


class ResourcesUnavailable(Exception):
    """Resources requested from a supply are not available"""
    __slots__ = 'claim',

    def __init__(self, claim: 'ClaimedResources'):
        self.claim = claim


class BaseResources(Generic[T]):
    """
    Internal base class for resource types
    """
    _levels_type = None  # type: Type[ResourceLevels[T]]
    _available = None  # type: Tracked[ResourceLevels[T]]

    @property
    def levels(self) -> ResourceLevels[T]:
        """Current levels of resources"""
        return self._available.value

    @property
    def resource_type(self) -> Type[ResourceLevels[T]]:
        """Type of underlying resources"""
        return self._levels_type

    async def __insert_resources__(self, amounts: ResourceLevels):
        new_levels = self._available.value + amounts
        await self._available.set(new_levels)

    async def __remove_resources__(self, amounts: ResourceLevels):
        new_levels = self._available.value - amounts
        await self._available.set(new_levels)

    def borrow(self, **amounts: T) -> 'BorrowedResources[T]':
        """
        Temporarily borrow resources for a given context

        :param amounts: resource levels to borrow
        :return: async context to borrow resources
        """
        borrowed_levels = self._levels_type(**amounts)
        assert self._levels_type.zero <= borrowed_levels,\
            'cannot borrow negative amounts'
        return BorrowedResources(self, borrowed_levels)

    def claim(self, **amounts: T) -> 'ClaimedResources[T]':
        """
        Temporarily borrow resources for a given context if available

        :param amounts: resource levels to borrow
        :return: async context to borrow resources
        :raises ResourcesUnavailable: if the claim is made as resources are unavailable
        """
        borrowed_levels = self.borrow(**amounts).limits
        return ClaimedResources(self, borrowed_levels)


class BorrowedResources(BaseResources[T]):
    """
    Fixed supply of named resources temporarily taken from another resource supply
    """
    @property
    def _levels_type(self):
        return self._resources._levels_type

    @property
    def limits(self):
        """Upper limit of resource levels"""
        return self._debits

    def __init__(self, resources: 'BaseResources', debits: ResourceLevels):
        self._resources = resources
        self._debits = debits
        self._available = Tracked(self._levels_type.zero)

    async def __aenter__(self):
        # do not postpone if we can resume immediately
        if not self._resources._available >= self._debits:
            await (self._resources._available >= self._debits)
        await self._resources.__remove_resources__(self._debits)
        await self.__insert_resources__(self._debits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is GeneratorExit:
            # we are killed forcefully and cannot perform async operations
            # dispatch a new activity to release our resources eventually
            __LOOP_STATE__.LOOP.schedule(
                self.__remove_resources__(self._debits)
            )
            __LOOP_STATE__.LOOP.schedule(
                self._resources.__insert_resources__(self._debits)
            )
        else:
            await self.__remove_resources__(self._debits)
            await self._resources.__insert_resources__(self._debits)
            # TODO: forcefully kill off anyone holding our resources?

    def borrow(self, **amounts: T) -> 'BorrowedResources[T]':
        borrowing = super().borrow(**amounts)
        assert self._debits >= borrowing._debits,\
            'cannot borrow beyond capacity'
        return borrowing


class ClaimedResources(BorrowedResources[T]):
    """
    Fixed supply of resources temporarily taken without delay
    """
    async def __aenter__(self):
        # do not postpone if we can resume immediately
        if not self._resources._available >= self._debits:
            raise ResourcesUnavailable(self)
        return await super().__aenter__()


class Capacities(BorrowedResources[T]):
    r"""
    Fixed supply of named resources which can be temporarily borrowed

    The resources and their maximum capacity are defined
    when the resource supply is created.
    Afterwards, it is only possible to temporarily :py:meth:`borrow`
    resources:

    .. code:: python3

        # create a limited supply of resources
        resources = Capacities(cores=8, memory=16000)

        # temporarily remove resources
        async with resources.borrow(cores=2, money=4000):
            await computation

    A :py:class:`~.Capacities` guarantees that its resources are conserved and
    cannot be leaked. Once resources are :py:meth:`~.borrow`\ ed, they can
    always be returned promptly.
    """
    def __init__(self, __zero__: Optional[T] = None, **capacity: T):
        resources = Resources(__zero__, **capacity)
        super().__init__(resources, resources.levels)
        self._available = Tracked(resources.levels)


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

    A :py:class:`~.Capacities` guarantees that it is always possible
    to increase the level of available resources.
    Once resources are :py:meth:`~.borrow`\ ed, they can
    always be returned promptly.
    """
    def __init__(self, __zero__: Optional[T] = None, **capacity: T):
        if not capacity:  # Note: this should be a type-error not assert for consistency
            raise TypeError(
                '%s requires at least 1 keyword-only argument' % self.__class__.__name__
            )
        __zero__ = __zero__ if __zero__ is not None else\
            type(next(iter(capacity.values())))()  # bare type invocation must be zero
        self._levels_type = __specialise__(__zero__, capacity.keys())
        self._available = Tracked(self._levels_type(**capacity))
        assert self._available >= self._levels_type.zero,\
            'initial capacities must be greater than or equal to zero'

    async def set(self, **amounts: T):
        """
        Set the level of resources

        :param amounts: resource levels to set

        Only levels of resources that are already part of these
        :py:class:`~.Resources` can be set. Levels cannot be set
        below zero. If a resource is not specified, its level remains
        unchanged.
        """
        assert self._levels_type.zero <= self._levels_type(**amounts),\
            'cannot increase by negative amounts'
        new_levels = dict(self._available.value).copy()
        new_levels.update(amounts)
        await self._available.set(self._levels_type(**new_levels))

    async def increase(self, **amounts: T):
        """
        Increase the level of resources

        :param amounts: resource levels to increase

        Only levels of resources that are already part of these
        :py:class:`~.Resources` can be increased. Levels cannot be increased
        by negative amounts. If a resource is not specified, its level remains
        unchanged.
        """
        delta = self._levels_type(**amounts)
        assert self._levels_type.zero <= delta,\
            'cannot increase by negative amounts'
        await self.__insert_resources__(delta)

    async def decrease(self, **amounts: T):
        """
        Decrease the level of resources

        :param amounts: resource levels to decrease

        Only levels of resources that are already part of these
        :py:class:`~.Resources` can be decreased. Levels cannot be decreased
        by negative amounts or below zero. If a resource is not specified, its
        level remains unchanged.
        """
        delta = self._levels_type(**amounts)
        assert self._levels_type.zero <= delta,\
            'cannot decrease by negative amounts'
        assert self._levels_type.zero <= (self._available.value - delta),\
            'cannot decrease below zero'
        await self.__remove_resources__(delta)
