from typing import TYPE_CHECKING, TypeVar, Generic, Union, Tuple, Optional, Generator,\
    List, Iterable
from .. import Flag, time
from .._primitives.condition import Any as AnyFlag

from .exceptions import CompatibilityError, Interrupt
if TYPE_CHECKING:
    from .core import Environment


# Implementation Note
# All of simpy's calls are sync, meaning we often *cannot* invoke
# the proper usim interfaces. Instead of recreating the usim primitives
# we use them anyways and directly manipulate them when required.
# For the most part, this means we use a ``usim.Flag`` for synchronisation.
# All ``async`` code uses its public interface, while compatiblity code directly
# accesses its internals.
#
# This is an ugly hack. Wherever possible, use the proper usim interfaces!


V = TypeVar('V')

__all__ = [
    'Event', 'Timeout', 'Process', 'Condition', 'ConditionValue', 'AllOf', 'AnyOf'
]


class Event(Generic[V]):
    """
    Explicitly triggered Event that processes can wait for

    An :py:class:`~.Event` is triggered by :py:meth:`~.succeed` or :py:meth:`~.fail`.
    Triggering wakes up every :py:class:`~.Process` or :py:class:`~usim.typing.Task`
    that is suspended waiting for the event. In addition, a :py:class:`~.Process` may
    add to the events :py:attr:`~.callbacks` to trigger actions alongside the event.

    .. code:: python3

        def track(event: Event):
            print('Waiting for %s' % event)
            yield event
            print('Notified by %s' % event)

        def trigger(event: Event):
            event.success("Jolly Good!")

    Once triggered, :py:attr:`~.value` is set either to the result or failure reason.

    Migrating to ``usim``
    ---------------------

    When migrating from :py:class:`~.Process` to :py:class:`~usim.typing.Task`,
    both can wait for an event. Simply ``await event`` from inside a :term:`Activity`:

        async def track(event: Event):
            print(f'Waiting for {event}')
            await event
            print(f'Notified by {event}')

    When migrating the :py:class:`~.Event`, the best match is :py:class:`usim.Flag`.
    A flag has no dedicated :py:attr:`~.value`, but represents a boolean.

    .. code:: python3

        async def track(flag: Flag):
            print(f'Waiting for {flag}')
            await flag
            print(f'Notified by {flag}')

        async def trigger(flag: Flag):
            await event.set()

    There is no concept for :py:attr:``~.callbacks`` and :py:attr:``~.defused``
    in ``usim``. Exceptions are propagated between activities and should be handled
    using ``try``/``except`` error handlers.
    """
    __slots__ = 'env', 'callbacks', '_flag', '_value', 'defused'

    def __init__(self, env: 'Environment'):
        self._flag = Flag()
        self.env = env
        self.callbacks = []  # type: List[Event]
        self._value = None  # type: Optional[Tuple[V, Optional[BaseException]]]
        self.defused = False

    # Implementation Note
    # ``usim`` would flatten Conditions of the same type here. With the
    # ``simpy`` model, this does not work well. The problem is that events
    # are active components that may fail the Environment.
    # If we flatten conditions, we end up with intermediate objects even in
    # trivial cases - a & b & c creates an intermediate pair of a & b. This
    # pair will evaluate concurrently, and is *not* defused on error.
    # So we *must* preserve all intermediate events to defuse them in one go.
    def __or__(self, other):
        if isinstance(other, Event):
            return AnyOf(self.env, (self, other))
        return NotImplemented

    def __and__(self, other):
        if isinstance(other, Event):
            return AllOf(self.env, (self, other))
        return NotImplemented

    def __await__(self):
        result = yield from self._flag.__await__()
        return result  # noqa: B901

    async def _invoke_callbacks(self):
        # simpy does this in core.Environment.step
        # we neither have step, nor a callback event loop
        assert self._value is not None,\
            f'{self.__class__.__name__} must be triggered before invoking callbacks'
        assert self.callbacks is not None,\
            f'{self.__class__.__name__} can invoke callbacks only once'
        callbacks, self.callbacks = self.callbacks, None
        for callback in callbacks:  # type: Event
            callback.trigger(self)
        value, exception = self._value
        if exception is not None and not self.defused:
            raise exception

    async def __usimpy_schedule__(self):
        """Coroutine to schedule this Event in ``usim.py``"""
        await self._invoke_callbacks()

    def _trigger(self):
        """Awake all waiting tasks and schedule the event itself"""
        self._flag._value = True
        self._flag.__trigger__()
        self.env.schedule(self)

    @property
    def triggered(self) -> bool:
        """Whether this event is being or has been processed"""
        return bool(self._flag)

    @property
    def processed(self) -> bool:
        """Whether the callbacks have been processed"""
        return self.callbacks is None

    @property
    def ok(self) -> bool:
        """Whether this event has been triggered successfully"""
        return self._value is not None and self._value[1] is None

    @property
    def value(self) -> Union[V, Exception]:
        """The value of the event if it has been triggered"""
        try:
            value, exception = self._value
        except TypeError:
            raise AttributeError(
                f"{self.__class__.__name__!r} object has no attribute 'value' set yet"
            )
        else:
            return value if exception is None else exception

    def trigger(self, event: 'Event') -> 'Event':
        """
        Trigger this event to match the state of ``event``

        :note: This method is invoked internally when running callbacks.
        """
        assert self._value is None, 'cannot trigger already triggered event'
        self._value = event._value
        self._trigger()
        return self  # simpy.Event docs say this, code does not

    def succeed(self, value=None) -> 'Event':
        """Trigger this event as successful with ``value``"""
        if self._value is not None:
            raise RuntimeError(f'{self} has already been triggered')
        self._value = value, None
        self._trigger()
        return self

    def fail(self, exception: BaseException):
        """Trigger this event as failed with ``exception``"""
        if self._value is not None:
            raise RuntimeError(f'{self} has already been triggered')
        if not isinstance(exception, BaseException):
            raise ValueError(
                'fail argument must be an exception,'
                f' not {exception.__class__.__name__!r}'
            )
        self._value = None, exception
        self._trigger()
        return self


class Timeout(Event[V]):
    """
    Automatically triggered Event that processes can wait for

    :param delay: time until the event is triggered
    :param value: value of the event when triggered

    Migrating to ``usim``
    ---------------------

    Time related notifications can be created using :py:data:`usim.time`.

    **timeout**
        Use ``await (time + delay)``.

    **deadline**
        Use ``await (time >= delay)`` or ``await (time == delay)``.
    """
    __slots__ = '_fixed_value', '_delay'

    def __init__(self, env, delay, value: Optional[V] = None):
        if delay < 0:
            raise ValueError("'delay' must not be negative")
        super().__init__(env)
        self._delay = delay
        self._fixed_value = value
        env.schedule(self._trigger_timeout())

    async def _trigger_timeout(self):
        await (time + self._delay)
        self.succeed(self._fixed_value)

    def __repr__(self):
        return f'<usim.py.{self.__class__.__name__} delay={self._delay}>'


class Initialize:
    """
    Internal initializer for :py:class:`~.Process`

    Since this event is internal and not used by 'usim.py',
    it is not implemented. Instantiating this class
    unconditionally raises an error.
    """
    def __init__(self, *args, **kwargs):
        raise CompatibilityError(self.__doc__)


class InterruptQueue:
    """
    Internal helper to manage interrupts for :py:class:`~.Process`
    """
    def __init__(self):
        self._flag = Flag()
        self._causes = []
        self.ok = False

    def __bool__(self):
        return bool(self._causes)

    @property
    def value(self):
        return Interrupt(self.pop())

    def push(self, cause):
        """Add a new interrupt with ``cause``"""
        self._causes.append(cause)
        if not self._flag:
            self._flag._value = True
            self._flag.__trigger__()

    def pop(self):
        result = self._causes.pop(0)
        if not self._causes:
            self._flag._value = False
        return result


class Process(Event[V]):
    """
    A concurrently running process which triggers as an event on completion

    Processes wrap around generators, which in turn may ``yield`` events to
    wait for them. This implements cooperative multitasking, allowing another
    process to run while others wait. Each :py:class:`~.Process` acts as an
    event which is automatically triggered when the underlying generator completes.

    .. code:: python3

        def clock(env: Environment, sound):
            for _ in range(60):
                print(sound)
                yield env.timeout(1)

        def clocks(env: Environment):
            env.process('tick')
            env.process('tack')
            yield env.process('TOCK')

    Migrating to ``usim``
    ---------------------

    When migrating from :py:class:`~.Process`, activities are expressed as
    ``async def`` coroutines instead of generators. Activities do not need
    an environment - it is implicitly available. An activity can ``await``
    a :term:`notification`, and concurrently iterate using ``async for``
    and manage resources using ``async with``.

    .. code:: python3

        async def clock(sound):
            for _ in range(60):
                print(sound)
                await (time + 1)

    To run an activity, one must distinguish between a concurrent
    :py:class:`~usim.typing.Task` and a nested activity. When an activity
    exclusively waits for another activity, this can be done directly using ``await``.

    .. code:: python3

        async def double_clock(sound):
            await clock(sound)
            await clock(sound)

    Only concurrent activities must be handled as a :py:class:`~usim.typing.Task`.
    Use a :py:class:`usim.Scope` to open new tasks and manage their lifetime:

    .. code:: python3

        async def multi_clock():
            async for Scope() as scope:
                scope.do(clock('tick'))
                scope.do(clock('tack'))
                scope.do(clock('TOCK'))
    """
    __slots__ = '_generator', '_interrupts'

    def __init__(self, env: 'Environment', generator: Generator[None, Event, V]):
        super().__init__(env)
        self._generator = generator
        self._interrupts = InterruptQueue()
        env.schedule(self._run_payload(), delay=0)

    def interrupt(self, cause=None):
        """Interrupt the process by raising a :py:exc:`Interrupt`"""
        if self._value is None:
            self._interrupts.push(cause)

    async def _run_payload(self):
        generator = self._generator
        interrupts = self._interrupts
        event = generator.send(None)  # type: Event
        while True:
            assert isinstance(event, Event),\
                f'process must yield an Event, not {event.__class__.__name__}'
            if not event.processed:
                await (event._flag | interrupts._flag)
            if interrupts:
                event = interrupts
            try:
                if event.ok:
                    event = generator.send(event.value)
                else:
                    # the process will handle the exception - or raise a new one
                    event.defused = True
                    event = generator.throw(event.value)
            except StopIteration as err:
                value = err.args[0] if err.args else None
                self.succeed(value)
                break
            except BaseException as err:
                self.fail(err)
                break

    @property
    def is_alive(self):
        """Whether the process is still running"""
        return self._value is not None

    def __repr__(self):
        return (
            f'<usim.py.{self.__class__.__name__} object'
            f' of {self._generator.__name__!r} at {id(self)}>'
        )


class ConditionValue:
    """
    ``dict``-like view to the events used in a condition and their value

    .. note::

        This type only captures the events, not their values.
        If the value of an event changes, this class reflects the change.
    """
    __slots__ = 'events',

    def __init__(self, *events: Event):
        self.events = events

    def __getitem__(self, item):
        if item not in self.events:
            raise KeyError(repr(item))
        return item.value

    def __contains__(self, item):
        return item in self.events

    def __eq__(self, other):
        if type(other) is ConditionValue:
            return self.events == other.events
        return self.todict() == other

    def __repr__(self):
        return (
            f'usim.py-events{self.__class__.__name__}'
            f'({", ".join(map(str, self.events))})'
        )

    def __iter__(self):
        yield from self.events

    keys = __iter__

    def values(self):
        return (event.value for event in self.events)

    def items(self):
        return zip(self, self.values())

    def todict(self):
        return dict(self.items())


class Condition(Event[ConditionValue]):
    """
    Event that is triggered when ``evaluate(events, num_triggered)`` is True

    On any change of events, ``evaluate`` is called with two arguments:
    ``events`` is a tuple of the events passed to the condition,
    and ``num_triggered`` is the number of events that have triggered so far.
    This can be used to quickly test how many events have triggered:

    .. code:: python3

        def most(events, count):
            "Test that at least 50% of events have triggered"
            return count * 2 >= len(events)

        majority = Condition(most, events)

    The value of a :py:class:`~.Condition` is a :py:class:`~.ConditionValue`
    of **all** the events used in the condition. Note that events of nested
    conditions are flattened. If *any* event fails, the :py:class:`~.Condition`
    fails with the same reason.

    .. note::

        The condition is only evaluated on instantiation and when child events
        trigger. This means that ``evaluate`` should not depend on external,
        mutable objects.

    Migrating to ``usim``
    ---------------------

    Since conditions, such as a :py:class:`~.Flag`, may change their value,
    ``usim`` does not support arbitrary comparisons. The common and well-defined
    :py:meth:`~.all_of` and :py:meth:`~.any_of` correspond to the ``&`` and ``|``
    operators.

    .. code:: python3

        all_events = flag1 & flag2 & flag3
        any_events = flag1 | flag2 | flag3
    """
    __slots__ = '_evaluate', '_events', '_processed'

    def __init__(self, env, evaluate, events: Iterable[Event]):
        super().__init__(env)
        self._evaluate = evaluate
        self._events = tuple(events)
        if any(event.env != env for event in self._events):
            raise ValueError('Events from multiple environments cannot be mixed')
        env.schedule(self._check_events(), delay=0)

    async def _check_events(self):
        observed = [event for event in self._events if event._flag]
        unobserved = [event for event in self._events if not event._flag]
        for event in observed:
            if not event.ok:
                # TODO: taken from simpy - this might swallow exceptions
                #       if event is awaited but self is not awaited
                event.defused = True
                self.fail(event.value)
                return
        while unobserved and not self._evaluate(self._events, len(observed)):
            await AnyFlag(*(event._flag for event in unobserved))
            for event in unobserved[:]:
                if not event._flag:
                    continue
                elif event.ok:
                    unobserved.remove(event)
                    observed.append(event)
                else:
                    event.defused = True
                    self.fail(event.value)
                    return
        if self._evaluate(self._events, len(observed)):
            self.succeed(ConditionValue(*self._flatten_values(self._events)))

    @classmethod
    def _flatten_values(cls, events) -> List[Event]:
        """Flatten the values of all events"""
        result = []
        for event in events:
            if isinstance(event, Condition):
                result.extend(cls._flatten_values(event._events))
            elif event.ok:
                result.append(event)
        return result

    @staticmethod
    def all_events(events, count):
        """Use as ``evaluate`` to test that all events have triggered"""
        return len(events) == count

    @staticmethod
    def any_events(events, count):
        """Use as ``evaluate`` to test that any events have triggered"""
        # TODO: taken from simpy - this is inconsistent with any([])
        return count or not events

    def __repr__(self):
        result = '' if self._value is None else (
            f', value={self._value[0]!r}' if self._value[1] is None else
            f', fail={self._value[1]!r}'
        )
        return (
            f'<usim.py.{self.__class__.__name__}'
            f' events=({", ".join(map(str, self._events))}){result}'
            f' at {id(self)}>'
        )


class AllOf(Condition):
    """
    Event that is triggered when all ``events`` have triggered

    Shorthand for ``Condition(Condition.all_events, events)``.
    """
    def __init__(self, env, events):
        super().__init__(env, self.all_events, events)


class AnyOf(Condition):
    """
    Event that is triggered when any ``events`` have triggered

    Shorthand for ``Condition(Condition.any_events, events)``.
    """
    def __init__(self, env, events):
        super().__init__(env, self.any_events, events)
