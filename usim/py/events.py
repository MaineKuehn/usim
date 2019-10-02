"""
This module provides the fundamental event types of SimPy:
:py:class:`~usim.py.events.Event`, :py:class:`~usim.py.events.Timeout` and
:py:class:`~usim.py.events.Process`.
All events are subclasses of :py:class:`~usim.py.events.Event`.

Simulations react to events by adding :py:attr:`~usim.py.events.Event.callbacks`
or by having a :py:class:`~usim.py.events.Process` ``yield`` an event to wait for.
A native μSim simulation can react to events by having an :term:`activity`
``await`` an event.
"""
from typing import TYPE_CHECKING, TypeVar, Generic, Union, Tuple, Optional, Generator,\
    List, Iterable, Callable, Awaitable
from .. import Flag, time
from .._primitives.condition import Any as AnyFlag

from .exceptions import NotCompatibleError, Interrupt, StopProcess
from ._awaitable import AwaitableEvent
if TYPE_CHECKING:
    from .core import Environment


# Implementation Note
# All of simpy's calls are synchronous, meaning we often *cannot* invoke
# the proper usim interfaces. Instead of recreating the usim primitives
# we use them anyways and directly manipulate them when required.
# For the most part, this means we use a ``usim.Flag`` for synchronisation.
# All ``async`` code uses its public interface, while compatiblity code directly
# accesses its internals.
#
# This is an ugly hack. Wherever possible, use the proper usim interfaces!


E = TypeVar('E')
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
    add to an event's :py:attr:`~.callbacks` to trigger actions alongside the event.

    .. code:: python3

        def track(event: Event):
            print('Waiting for %s' % event)
            yield event
            print('Notified by %s' % event)

        def trigger(event: Event):
            event.success("Jolly Good!")

    Once triggered, :py:attr:`~.value` is set either to the result or failure reason.
    Use :py:attr:`~.triggered`, :py:attr:`~.processed`, and :py:attr:`~.ok` to inspect
    what state an event is in.

    .. hint::

        **Migrating to μSim**

        When migrating from :py:class:`~.Process` to :py:class:`~usim.typing.Task`,
        both can wait for an event. Use ``await event`` inside an :term:`Activity`:

        .. code:: python3

            async def track(event: Event):
                print(f'Waiting for {event}')
                await event
                print(f'Notified by {event}')

        The value is returned on success of the event, and raised on failure.

        When migrating the :py:class:`~.Event`, the best match is :py:class:`usim.Flag`.
        A flag has no dedicated :py:attr:`~.value`, but represents a boolean.

        .. code:: python3

            async def track(flag: Flag):
                print(f'Waiting for {flag}')
                await flag
                print(f'Notified by {flag}')

            async def trigger(flag: Flag):
                await event.set()

        In order to send values between activities, use a :py:class:`usim.basics.Queue`
        or :py:class:`usim.basics.Channel`. These allow to send and wait for messages.

        .. code:: python3

            async def receiver(queue: Queue):
                print('Waiting for a message to reach us...')
                message = await queue
                print(f'And the message is: {message}')

            async def sender(queue: Queue):
                await queue.put('Hello World')

        There is no concept for :py:attr:``~.callbacks`` and :py:attr:``~.defused``
        in μSim. Exceptions are propagated between activities and should be handled
        using ``try``/``except`` error handlers.
    """
    __slots__ = 'env', 'callbacks', '__usimpy_flag__', '_value', 'defused'

    def __init__(self: E, env: 'Environment'):
        self.__usimpy_flag__ = Flag()
        #: The environment to which this event belongs
        self.env = env
        #: List of callbacks to run when the event is triggered
        self.callbacks = []  # type: List[Callable[[E], None]]
        self._value = None  # type: Optional[Tuple[V, Optional[BaseException]]]
        #: Whether a failure of this event has been handled
        self.defused = False

    # Implementation Note
    # ``usim`` would flatten Conditions of the same type here. With the
    # ``simpy`` model, this does not work. The problem is that events
    # are active components that make the Environment fail.
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
        yield from self.__usimpy_flag__.__await__()
        result, error = self._value
        if error is not None:
            # the waiter will handle our exception
            self.defused = True
            raise error
        else:
            return result  # noqa: B901

    async def _invoke_callbacks(self):
        # simpy does this in core.Environment.step
        # we neither have step, nor a callback event loop
        assert self._value is not None,\
            f'{self.__class__.__name__} must be triggered before invoking callbacks'
        assert self.callbacks is not None,\
            f'{self.__class__.__name__} can invoke callbacks only once'
        callbacks, self.callbacks = self.callbacks, None
        for callback in callbacks:  # type: Callable[[E], None]
            callback(self)
        value, exception = self._value
        if exception is not None and not self.defused:
            raise exception

    async def __usimpy_schedule__(self):
        """Coroutine to schedule this Event in ``usim.py``"""
        await self._invoke_callbacks()

    def _trigger(self):
        """Awake all waiting tasks and schedule the event itself"""
        self.__usimpy_flag__._value = True
        self.__usimpy_flag__.__trigger__()
        self.env.schedule(self)

    @property
    def triggered(self) -> bool:
        """Whether this event is being or has been processed"""
        return bool(self.__usimpy_flag__)

    @property
    def processed(self) -> bool:
        """Whether the callbacks have been processed"""
        return self.callbacks is None

    @property
    def ok(self) -> bool:
        """
        Whether this event has been processed successfully

        .. hint::

            Migrate by using ``bool(flag)`` instead.
        """
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
        Trigger this event and inherit the value or exception of ``event``

        .. note::

            This method is invoked internally when running callbacks.
            Avoid using it manually.
        """
        assert self._value is None, 'cannot trigger already triggered event'
        self._value = event._value
        self._trigger()
        return self  # simpy.Event docs say this, code does not

    def succeed(self, value=None) -> 'Event':
        """
        Trigger this event as successful with ``value``

        .. hint::

            Migrate by using ``flag.set()`` instead.
        """
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

    This event does automatically :py:meth:`~.succeed` after ``delay``
    has passed. It should not be triggered manually.

    :param delay: time until the event is triggered
    :param value: value of the event when triggered

    .. hint::

        **Migrating to μSim**

        Time related notifications can be created using :py:data:`usim.time`.

        **timeout**
            Use ``await (time + delay)``.

        **deadline**
            Use ``await (time >= deadline)`` or ``await (time == deadline)``.
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
        raise NotCompatibleError(self.__doc__)


class InterruptQueue:
    """
    Internal helper to manage interrupts for :py:class:`~.Process`
    """
    __slots__ = '__usimpy_flag__', '_causes', 'ok', 'defused'

    def __init__(self):
        self.__usimpy_flag__ = Flag()
        self._causes = []
        self.ok = False
        self.defused = True

    def __bool__(self):
        return bool(self._causes)

    @property
    def value(self):
        """The next :py:exc:`Interrupt`; this is a destructive action"""
        return Interrupt(self.pop())

    def push(self, cause):
        """Add a new interrupt with ``cause``"""
        self._causes.append(cause)
        if not self.__usimpy_flag__:
            self.__usimpy_flag__._value = True
            self.__usimpy_flag__.__trigger__()

    def pop(self):
        result = self._causes.pop(0)
        if not self._causes:
            self.__usimpy_flag__._value = False
        return result


class Process(Event[V]):
    """
    A concurrently running process which triggers as an event on completion

    Processes wrap around generators, which in turn may ``yield`` events to
    wait for them. This implements cooperative multitasking, allowing another
    process to run while others wait. Each :py:class:`~.Process` acts as an
    event which is automatically triggered when the underlying generator completes.

    .. code:: python3

        def go_to(env: Environment, destination: str, duration: float):
            print('Driving to %s' % destination)
            yield env.timeout(duration)
            print('Arrived at %s' % destination)

        def visit_many(env, *destinations: str):
            '''Visit all destinations one after the other'''
            for destination in destinations:
                # yield a process to wait for its completion
                yield env.process(go_to(env, destination, len(destination))

    A Process can also be created without waiting for it.
    In this case, the newly created process has no connection to its parent process.

    .. code:: python3

        def dispatch(env: Environment, destinations: List[str], drivers: List[str]):
            for destination, driver in zip(destinations, drivers):
                print('Sending %s to %s' % (driver, destination))
                env.process(go_to(env, destination, len(destination))

    .. hint::

        **Migrating to μSim**

        When migrating from :py:class:`~.Process`, activities are expressed as
        ``async def`` coroutines instead of generators. Activities do not need
        an environment - it is implicitly available. An activity can ``await``
        a :term:`notification`, concurrently iterate using ``async for``
        and manage resources using ``async with``.

        .. code:: python3

            async def go_to(destination: str, duration: float):
                print(f'Driving to {destination}')
                await (time + duration)
                print(f'Arrived at {destination}')

        To run an activity, one must distinguish between a concurrent
        :py:class:`~usim.typing.Task` and a nested activity. When an activity
        exclusively waits for another activity, it can directly ``await`` it.

        .. code:: python3

            async def visit_many(*destinations: str):
                '''Visit all destinations one after the other'''
                for destination in destinations:
                    # await a bare activity to wait for its completion
                    await go_to(destination, len(destination)

        Only concurrent activities must be handled as a :py:class:`~usim.typing.Task`.
        Use a :py:class:`usim.Scope` to open new tasks and manage their lifetime
        -- the parent activity will automatically manage its child activities.

        .. code:: python3

            async def dispatch(destinations: List[str], drivers: List[str]):
                async for Scope() as scope:
                    for destination, driver in zip(destinations, drivers):
                        print(f'Sending {driver} to {destination}')
                        scope.do(go_to(destination, len(destination))
    """
    __slots__ = '_generator', '_interrupts', 'target'

    def __init__(self, env: 'Environment', generator: Generator[None, Event, V]):
        if not hasattr(generator, 'send') and not hasattr(generator, 'throw'):
            raise ValueError(
                f"'generator' argument must implement 'throw' and 'send'"
            )
        super().__init__(env)
        self._generator = generator
        self._interrupts = InterruptQueue()
        #: Event this process is waiting for, or :py:const:`None` if
        #: the process is starting, stopping or about to be interrupted
        self.target = None  # type: Optional[Event]
        env.schedule(self._run_payload(), delay=0)

    def interrupt(self, cause=None):
        """Interrupt the process by raising an :py:exc:`Interrupt`"""
        if self._value is None:
            self._interrupts.push(cause)

    async def _run_payload(self):
        generator = self._generator
        interrupts = self._interrupts
        env = self.env
        env.active_process = self
        self.target = event = generator.send(None)  # type: Event
        env.active_process = None
        while True:
            event = await self._wait_interruptible(event, interrupts)
            try:
                if event.ok:
                    env.active_process = self
                    self.target = event = generator.send(event.value)
                    env.active_process = None
                else:
                    # the process will handle the exception - or raise a new one
                    event.defused = True
                    env.active_process = self
                    self.target = event = generator.throw(event.value)
                    env.active_process = None
            except (StopIteration, StopProcess) as err:
                value = err.args[0] if err.args else None
                self.succeed(value)
                break
            except BaseException as err:
                self.fail(err)
                break

    async def _wait_interruptible(
        self, event: Union[Awaitable, Event], interrupts: InterruptQueue
    ) -> Union[Event, AwaitableEvent, InterruptQueue]:
        """Wait for the ``event`` or an interrupt to occur"""
        if isinstance(event, Awaitable) and not isinstance(event, Event):
            event = AwaitableEvent(event)
            finished = await event.wait_interruptible(interrupts.__usimpy_flag__)
            if finished:
                return event
            else:
                return interrupts
        else:
            assert isinstance(event, Event),\
                f'process {self._generator} must yield an Event,'\
                f' not {event.__class__.__name__}'
            if not event.processed:
                await (event.__usimpy_flag__ | interrupts.__usimpy_flag__)
            if interrupts:
                event = interrupts
                self.target = None
            return event

    @property
    def is_alive(self):
        """Whether the process is still running"""
        return self._value is None

    def __repr__(self):
        return (
            f'<usim.py.{self.__class__.__name__} object'
            f' of {self._generator.__name__!r} at {id(self)}>'
        )


class ConditionValue:
    """
    ``dict``-like view to the events used in a condition and their values

    .. note::

        This type only captures the events, not their values.
        If the value of a contained event changes,
        the value in the ConditionValue changes as well.
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
            '''Test that at least 50% of events have triggered'''
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

    .. hint::

        **Migrating to μSim**

        Since conditions, such as a :py:class:`~.Flag`, may change their value,
        μSim does not support arbitrary comparisons. The common and well-defined
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
        observed, unobserved = 0, []
        for event in self._events:
            if not event.__usimpy_flag__:
                unobserved.append(event)
            elif not event.ok:
                # TODO: taken from simpy - this might swallow exceptions
                #       if event is awaited but self is not awaited
                event.defused = True
                self.fail(event.value)
                return
            else:
                observed += 1
        while unobserved and not self._evaluate(self._events, observed):
            await AnyFlag(*(event.__usimpy_flag__ for event in unobserved))
            for event in unobserved[:]:
                if not event.__usimpy_flag__:
                    continue
                elif event.ok:
                    unobserved.remove(event)
                    observed += 1
                else:
                    event.defused = True
                    self.fail(event.value)
                    return
        if self._evaluate(self._events, observed):
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
    __slots__ = ()

    def __init__(self, env, events):
        super().__init__(env, self.all_events, events)


class AnyOf(Condition):
    """
    Event that is triggered when any ``events`` have triggered

    Shorthand for ``Condition(Condition.any_events, events)``.
    """
    __slots__ = ()

    def __init__(self, env, events):
        super().__init__(env, self.any_events, events)
