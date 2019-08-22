"""
For simulation time there is no inherent time unit, such as seconds,
hours, or years, implied.
A simulation should use a consistent time unit, however.

The default time type is :py:class:`float`, which in principle may exhibit
imprecision for fractions.
Using the standard SI unit of seconds on a 64bit machine,
time can represent more than 285 million years of time accurately.

:note: When using a time of :py:class:`float` and reaching ``Time().now == math.inf``,
       it is still not possible to reach :py:class:`Eternity`.
       This may change in the future.
"""
from typing import Coroutine, Generator, Any, AsyncIterable

from .._core.loop import __LOOP_STATE__, __HIBERNATE__, Interrupt as CoreInterrupt
from .notification import postpone, Notification
from .condition import Condition


class After(Condition):
    r"""
    The time range at and after a certain point in time

    :param target: point in time from which on this condition is :py:const:`True`

    The time range is *inclusive* of the time at `target`.
    If `await`\ ed before `target`, an :term:`activity` is
    :term:`suspended <Suspension>` until :term:`time` is advanced to `target`.
    If `await`\ ed at or after `target`, an :term:`activity` is
    :term:`postponed <Postponement>`.

    The expression ``time >= target`` is equivalent to ``After(target)``.
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

    def __await__(self) -> Generator[Any, None, bool]:
        # we will *always* wake up once the target has passed
        # either we wake up in the same time frame,
        # or just wait for a single trigger
        if self:
            yield from postpone().__await__()
            return True
        self._ensure_trigger()
        yield from Notification.__await__(self)
        return True  # noqa: B901

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._ensure_trigger()
        super().__subscribe__(waiter, interrupt)

    def __repr__(self):
        return '{self.__class__.__name__}({self.target})'.format(self=self)

    def __str__(self):
        return 'usim.time >= {}'.format(self.target)


class Before(Condition):
    r"""
    The time range before a certain point in time

    :param target: point in time before which this condition is :py:const:`True`

    The time range is *exclusive* of the time at `target`.
    If `await`\ ed before `target`, an :term:`activity` is
    :term:`postponed <Postponement>`.
    If `await`\ ed at or after `target`, an :term:`activity` is
    :term:`suspended <Suspension>` until :term:`time` is advanced to `target`.

    The expression ``time < target`` is equivalent to ``Before(target)``.
    """
    __slots__ = ('target',)

    def __init__(self, target: float):
        super().__init__()
        self.target = target

    def __bool__(self):
        return __LOOP_STATE__.LOOP.time < self.target

    def __invert__(self):
        return After(self.target)

    def __await__(self) -> Generator[Any, None, bool]:
        # we will *never* wake up once the target has passed
        # either we wake up in the same time frame,
        # or just hibernate indefinitely
        if self:
            yield from postpone().__await__()
        else:
            yield from __HIBERNATE__
        return True  # noqa: B901

    def __repr__(self):
        return '{self.__class__.__name__}({self.target})'.format(self=self)

    def __str__(self):
        return 'usim.time < {}'.format(self.target)


class Moment(Condition):
    r"""
    A certain point in time

    :param target: point in time during which this condition is :py:const:`True`

    If `await`\ ed before `target`, an :term:`activity` is
    :term:`suspended <Suspension>` until :term:`time` is advanced to `target`.
    If `await`\ ed at `target`, an :term:`activity` is
    :term:`postponed <Postponement>`.
    If `await`\ ed after `target`, an :term:`activity` is
    :term:`suspended <Suspension>` indefinitely.

    The expression ``time == target`` is equivalent to ``Moment(target)``.
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
        raise NotImplementedError(
            "Inverting a moment is not well-defined\n\n"
            "The inverse implies the moment immediately before or after another,\n"
            "i.e. '(time < date | time > date)'. The latter term is not\n"
            "a meaningful event."
        )

    def __await__(self) -> Generator[Any, None, bool]:
        # we will *never* wake up once the target has passed
        # either we wake up in the same time frame,
        # or just hibernate indefinitely
        if __LOOP_STATE__.LOOP.time == self.target:
            yield from postpone().__await__()
        elif not self._transition:
            yield from self._transition.__await__()
        else:
            yield from __HIBERNATE__
        return True  # noqa: B901

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._transition.__subscribe__(waiter, interrupt)

    def __unsubscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._transition.__unsubscribe__(waiter, interrupt)

    def __repr__(self):
        return '{self.__class__.__name__}({self.target})'.format(self=self)

    def __str__(self):
        return 'usim.time == {}'.format(self.target)


class Eternity(Condition):
    r"""
    A future point in time infinitely far into the future

    An :term:`activity` that `await`\ s :py:class:`~.Eternity`
    is never woken up by itself.
    This holds true even when :term:`time` advances to :py:data:`math.inf`
    or another representation of infinity.

    .. code:: python

        await Eternity()  # wait forever
    """
    __slots__ = ()

    def __bool__(self):
        return False

    def __invert__(self):
        return Instant()

    def __await__(self) -> Generator[Any, None, bool]:
        yield from __HIBERNATE__
        return True  # noqa: B901

    def __repr__(self):
        return '{self.__class__.__name__}()'.format(self=self)

    def __str__(self):
        return 'usim.eternity'


class Instant(Condition):
    r"""
    A future point in time indistinguishable from the current time

    An :term:`activity` that `await`\ s :py:class:`~.Instant`
    is merely :term:`postponed <Postponement>`.
    The current :term:`time` has no effect on this.

    .. code:: python

        await Instant()  # wait shortly, resuming in the same time step
    """
    __slots__ = ()

    def __bool__(self):
        return True

    def __invert__(self):
        return Eternity()

    def __await__(self) -> Generator[Any, None, bool]:
        yield from postpone().__await__()
        return True  # noqa: B901

    def __repr__(self):
        return '{self.__class__.__name__}()'.format(self=self)

    def __str__(self):
        return 'usim.instant'


class Delay(Notification):
    r"""
    A relative delay from the current time

    :param duration: delay in time after which this condition is :py:const:`True`

    A :py:class:`~.Delay` does not form a :py:class:`~.Condition`.
    The ``delay`` is always in relation to the current time:
    every time a :py:class:`~.Delay` is `await`\ ed creates a new
    :term:`event`.

    .. code:: python3

        delay = time + 20
        await delay      # delay for 20
        await delay      # delay for 20 again
        print(time.now)  # gives 40

    The expression ``time + duration`` is equivalent to ``Delay(duration)``.
    """
    __slots__ = ('duration',)

    def __init__(self, duration: float):
        super().__init__()
        self.duration = duration

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        interrupt.scheduled = True
        __LOOP_STATE__.LOOP.schedule(waiter, interrupt, delay=self.duration)

    def __repr__(self):
        return '{self.__class__.__name__}({self.duration})'.format(self=self)

    def __str__(self):
        return 'usim.time + {}'.format(self.duration)


class Time:
    r"""
    Representation of ongoing simulation time

    .. code:: python

        now = time.now        # get the current time
        await (time + 20)     # wait for a time span to pass
        await (time == 1999)  # wait for a time date to occur
        await (time >= 1999)  # wait for a time date to occur or pass

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

    :note: There is no need to instantiate :py:class:`Time` as it is stateless.
           Use the instance :py:data:`usim.time` instead.
    """
    __slots__ = ()

    @property
    def now(self) -> float:
        """The current simulation time"""
        return __LOOP_STATE__.LOOP.time

    def __add__(self, other: float) -> Delay:
        return Delay(other)

    def __ge__(self, other: float) -> After:
        return After(other)

    def __eq__(self, other: float) -> Moment:
        return Moment(other)

    def __lt__(self, other: float) -> Before:
        return Before(other)

    if __debug__:
        def __le__(self, other):
            raise TypeError((
                "'<=' not supported between 'time' and instances of '%s'\n\n"
                "Only 'now and after' (time >= date) is well-defined,\n"
                "but 'now and before' (time <= date) is not. Use instead:\n"
                "* 'await (time < date)' to not wait before a point in time\n"
                "* 'await (time >= date)' to not wait after or at a point in time\n"
                "\n"
                "To test 'now is before or at a point in time', use 'time.now <= date'"
            ) % type(other).__name__)

        def __gt__(self, other):
            raise TypeError((
                "'>' not supported between 'time' and instances of '%s'\n\n"
                "Only 'before' (time < date) is well-defined,\n"
                "but 'after' (time > date) is not. Use instead:\n"
                "* 'await (time < date)' to not wait before a point in time\n"
                "* 'await (time >= date)' to not wait after or at a point in time\n"
                "\n"
                "To test 'now is after a point in time', use 'time.now > date'"
            ) % type(other).__name__)

        def __await__(self):
            raise TypeError(
                "'time' cannot be used in 'await' expression\n\n"
                "Use 'time' to derive operands for specific expressions:\n"
                "* 'await (time + duration)' to delay for a specific duration\n"
                "* 'await (time == date)' to proceed at a specific point in time\n"
                "* 'await (time >= date)' to proceed at or after a point in time\n"
                "* 'await (time < date)' to indefinitely block after a point in time\n"
                "\n"
                "To get the current time, use 'time.now'"
            )

    def __repr__(self):
        try:
            now = self.now
        except RuntimeError:
            return '<detached handle usim.time>'
        else:
            return '<attached handle usim.time @ {now}>'.format(now=now)


time = Time()


async def each_interval(interval: float):
    loop = __LOOP_STATE__.LOOP
    last_time = loop.time
    while True:
        await (time == last_time + interval)
        last_time = loop.time
        yield last_time


async def each_delay(delay: float):
    loop = __LOOP_STATE__.LOOP
    waiter = time + delay
    while True:
        await waiter
        yield loop.time


def each(
        *, delay: float = None, interval: float = None
) -> AsyncIterable[float]:
    """
    Iterate through time by either ``delay`` or ``interval``

    :param delay: on each step, pause for ``delay``
    :param interval: on each step, pause until ``interval`` since the last step
    :raises TypeError: if both ``delay`` and ``interval`` are provided

    Asynchronous iteration pauses and provides the current time at each step.

    .. code:: python3

        print('It was', time.now)  # 0
        async for now in each(delay=10):
            print('It is', now)  # 10, 20, 30, ...

    The first pause occurs *before* entering the loop body.

    Setting `delay`` causes iteration to always *pause for* the same time,
    even if the current activity is :term:`suspended <Suspension>`
    in the loop body.
    Setting ``interval`` causes iteration to *resume at* regular times,
    even if the current activity is :term:`suspended <Suspension>`
    in the loop body - the pause is shortened if necessary.

    .. code:: python3

        async for now in each(interval=10):
            await (time + 1)
            print(now, time.now)  # (10, 11), (20, 21), (30, 31), ...

        async for now in each(delay=10):
            await (time + 1)
            print(now, time.now)  # (10, 11), (21, 22), (32, 33), ...
    """
    if delay is not None and interval is None:
        return each_delay(delay)
    elif interval is not None and delay is None:
        return each_interval(interval)
    else:
        raise TypeError("each() got conflicting arguments 'delay' and 'interval'")
