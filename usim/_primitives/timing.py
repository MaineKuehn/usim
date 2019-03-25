"""
There is no inherent time unit, such as seconds, hours, or years, implied for simulation time.
A simulation should use a consistent time unit, however.

The default time type is :py:class:`float`, which in principle may exhibit imprecision for fractions.
Using the standard SI unit of seconds on a 64bit machine,
time can represent more than 285 million years of time accurately.

:note: When using a time of :py:class:`float` and reaching ``Time().now == math.inf``,
       it is still not possible to reach :py:class:`Eternity`.
       This may change in the future.
"""
from math import inf

from typing import Awaitable, Coroutine, Union

from .._core.loop import __LOOP_STATE__, Hibernate, Interrupt as CoreInterrupt
from .notification import postpone, Notification
from .condition import Condition


class After(Condition):
    r"""
    The time range at and after a certain point in time

    :param target: point in time after which this condition is :py:const:`True`

    The time range is *inclusive* of the time at `target`.
    If `await`\ ed before `target`, :py:class:`After` proceeds in the :py:class:`Moment` of `target`.
    Otherwise, it proceeds in an :py:class:`Instant`.
    """
    __slots__ = ('target', '_scheduled')

    def __init__(self, target: float):
        super().__init__()
        self.target = target
        self._scheduled = None

    def __bool__(self):
        return __LOOP_STATE__.LOOP.time >= self.target

    def __invert__(self):
        return Before(self.target)

    def _ensure_trigger(self):
        if not self._scheduled:
            self._scheduled = True
            __LOOP_STATE__.LOOP.schedule(self._async_trigger(), at=self.target)

    # we cannot schedule __trigger__ directly, since it is not async
    async def _async_trigger(self):
        self.__trigger__()

    def __await__(self) -> Awaitable[bool]:
        # we will *always* wake up once the target has passed
        # either we wake up in the same time frame,
        # or just wait for a single trigger
        if self:
            yield from postpone().__await__()
            return True
        self._ensure_trigger()
        yield from Notification.__await__(self)
        return True

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._ensure_trigger()
        super().__subscribe__(waiter, interrupt)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.target)


class Before(Condition):
    r"""
    The time range before a certain point in time

    :param target: point in time before which this condition is :py:const:`True`

    The time range is *exclusive* of the time at `target`.
    """
    __slots__ = ('target',)

    def __init__(self, target: float):
        super().__init__()
        self.target = target

    def __bool__(self):
        return __LOOP_STATE__.LOOP.time < self.target

    def __invert__(self):
        return After(self.target)

    def __await__(self) -> Awaitable[bool]:
        # we will *never* wake up once the target has passed
        # either we wake up in the same time frame,
        # or just hibernate indefinitely
        if self:
            yield from postpone().__await__()
        else:
            yield from Hibernate().__await__()
        return True

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.target)


class Moment(Condition):
    r"""
    A certain point in time

    :param target: point in time during which this condition is :py:const:`True`
    """
    __slots__ = ('target', '_transition')

    def __init__(self, target: float):
        super().__init__()
        self.target = target
        # notification point at which we transition from before to after
        self._transition = After(target)

    def __bool__(self):
        return __LOOP_STATE__.LOOP.time == self.target

    def __invert__(self):
        raise NotImplementedError

    def __await__(self) -> Awaitable[bool]:
        # we will *never* wake up once the target has passed
        # either we wake up in the same time frame,
        # or just hibernate indefinitely
        if __LOOP_STATE__.LOOP.time == self.target:
            yield from postpone().__await__()
        elif not self._transition:
            yield from self._transition.__await__()
        else:
            yield from Hibernate().__await__()
        return True

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._transition.__subscribe__(waiter, interrupt)

    def __unsubscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._transition.__unsubscribe__(waiter, interrupt)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.target)


class Eternity(Condition):
    r"""
    A future point in time infinitely far into the future

    .. code:: python

        await Eternity()  # wait forever
    """
    __slots__ = ()

    def __bool__(self):
        return False

    def __invert__(self):
        return Instant()

    def __await__(self) -> Awaitable[bool]:
        yield from Hibernate().__await__()


class Instant(Condition):
    r"""
    A future point in time indistinguishable from the current time

    .. code:: python

        await Instant()  # wait shortly, resuming in the same time step
    """
    __slots__ = ()

    def __bool__(self):
        return True

    def __invert__(self):
        return Eternity()

    def __await__(self) -> Awaitable[bool]:
        yield from postpone().__await__()
        return True


class Delay(Notification):
    r"""
    A relative delay from the current time
    """
    __slots__ = ('duration',)

    def __init__(self, duration: float):
        super().__init__()
        self.duration = duration

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        interrupt.scheduled = True
        __LOOP_STATE__.LOOP.schedule(waiter, interrupt, delay=self.duration)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.duration)


class Time:
    r"""
    Representation of ongoing simulation time

    .. code:: python

        now = time.now        # get the current time
        await (time + 20)     # wait for a time span to pass
        await (time == 1999)  # wait for a time date to occur

        async with until(time + 20):  # abort block after a delay
            ...

        async with until(time == 1999):  # abort block at a fixed time
            await party()

    Due to the nature of simulated time there is only "directly after" any
    specific point in time, but not "directly before".
    This allows to express only "strictly before" (``time < point``),
    and "equal or after" (``time >= point``) as ``await``\ able events.

    However, it is possible to *test* e.g. "equal or before" using the
    current time (``time.now <= point``).
    To avoid accidental mixing of ``await``\ able and non-\ ``await``\ able
    comparisons, :py:class:`Time` does not support the later.
    """
    __slots__ = ()

    @property
    def now(self) -> float:
        """The current simulation time"""
        return __LOOP_STATE__.LOOP.time

    def __add__(self, other: float) -> Delay:
        return Delay(other)

    def __ge__(self, other: float) -> Condition:
        if other is inf:
            return Eternity()
        return After(other)

    def __eq__(self, other: float) -> Moment:
        return Moment(other)

    def __lt__(self, other: float) -> Before:
        return Before(other)


time = Time()


class IntervalIter:
    __slots__ = ('interval', '_last')

    def __init__(self, interval: float):
        self.interval = interval
        self._last = None

    async def __anext__(self):
        if self._last is None:
            self._last = __LOOP_STATE__.LOOP.time - self.interval
        await (time == self._last + self.interval)
        self._last = time.now
        return self._last

    def __aiter__(self):
        return self


class DurationIter:
    __slots__ = ('delay',)

    def __init__(self, delay: float):
        self.delay = delay

    async def __anext__(self):
        await (time + self.delay)
        return time.now

    def __aiter__(self):
        return self


def each(*, delay: float = None, interval: float = None) -> Union[DurationIter, IntervalIter]:
    if delay is not None and interval is None:
        return DurationIter(delay)
    elif interval is not None and delay is None:
        return IntervalIter(interval)
    else:
        raise ValueError("exactly one of 'delay' or 'interval' must be used")
