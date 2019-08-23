from typing import TYPE_CHECKING, TypeVar, Generic, Union, Tuple, Optional, Generator,\
    List, Iterable
from .. import Flag, time
from .._primitives.condition import Any as AnyFlag

from .exceptions import CompatibilityError, Interrupt
if TYPE_CHECKING:
    from .core import Environment


T = TypeVar('T')

__all__ = [
    'Event', 'Timeout', 'Process', 'Condition', 'ConditionValue', 'AllOf', 'AnyOf'
]


class Event(Generic[T]):
    __slots__ = 'env', 'callbacks', '_flag', '_value', 'defused'

    def __init__(self, env: 'Environment'):
        self._flag = Flag()
        self.env = env
        self.callbacks = []  # type: List[Event]
        self._value = None  # type: Optional[Tuple[T, Optional[BaseException]]]
        self.defused = False

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
        if exception is not None:
            raise exception

    async def __usimpy_schedule__(self):
        """Coroutine to schedule this Event in ``usim.py``"""
        await self._flag.set()
        await self._invoke_callbacks()

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
    def value(self) -> Union[T, Exception]:
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
        self.env.schedule(self)
        return self  # simpy.Event docs say this, code does not

    def succeed(self, value=None) -> 'Event':
        """Trigger this event as successful with ``value``"""
        if self._value is not None:
            raise RuntimeError(f'{self} has already been triggered')
        self._value = value, None
        self.env.schedule(self)
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
        self.env.schedule(self)
        return self


class Timeout(Event[T]):
    __slots__ = '_fixed_value', '_delay'

    def __init__(self, env, delay, value: Optional[T] = None):
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
        return f'<{self.__class__.__name__} delay={self._delay}>'


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
        self._causes.append(cause)
        if not self._flag:
            self._flag._value = True
            self._flag.__trigger__()

    def pop(self):
        result = self._causes.pop(0)
        if not self._causes:
            self._flag._value = False
        return result


class Process(Event[T]):
    __slots__ = '_generator', '_interrupts'

    def __init__(self, env: 'Environment', generator: Generator[None, Event, T]):
        super().__init__(env)
        self._generator = generator
        self._interrupts = InterruptQueue()
        env.schedule(self._run_payload(), delay=0)

    def interrupt(self, cause=None):
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
        return self._value is not None

    def __repr__(self):
        return (
            f'<{self.__class__.__name__} object'
            f' of {self._generator.__name__!r} at {id(self)}>'
        )


class ConditionValue:
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
        return f'{self.__class__.__name__}({", ".join(map(str, self.events))})'

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
    __slots__ = '_evaluate', '_events', '_processed'

    def __init__(self, env, evaluate, events: Iterable[Event]):
        super().__init__(env)
        self._evaluate = evaluate
        self._events = tuple(events)
        if any(event.env != env for event in self._events):
            raise ValueError('Events from multiple environments cannot be mixed')

    async def _check_events(self):
        observed = [event for event in self._events if event._flag]
        unobserved = [event for event in self._events if not event._flag]
        for event in observed:
            if not event.ok:
                # TODO: taken from simpy - this might swallow exceptions
                #       if event is awaited but not self is not awaited
                event.defused = True
                self.fail(event.value)
                return
        while unobserved and not self._evaluate(self._events, len(observed)):
            await AnyFlag(*unobserved)
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
            elif event.processed:
                result.append(event)
        return result

    @staticmethod
    def all_events(events, count):
        return len(events) == count

    @staticmethod
    def any_events(events, count):
        # TODO: taken from simpy - this is inconsistent with any([])
        return count or not events


class AllOf(Condition):
    def __init__(self, env, events):
        super().__init__(env, self.all_events, events)


class AnyOf(Condition):
    def __init__(self, env, events):
        super().__init__(env, self.any_events, events)
