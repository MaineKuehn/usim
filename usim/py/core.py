from typing import Optional, List, Tuple, Coroutine, Generator, TypeVar, Iterable,\
    NoReturn, Union
from .._core.loop import __LOOP_STATE__, Loop
from .. import time, run as usim_run
from .. import Scope

from .events import Event
from .exceptions import CompatibilityError, StopSimulation


class EnvironmentScope(Scope):
    def _handle_exception(self, exc_val):
        return isinstance(exc_val, StopSimulation)


V = TypeVar('V')


class Environment:
    """
    SimPy Environment compatibility layer embedded in a ``usim`` simulation

    .. code:: python3

        async def legacy_simulation():
            async with EmbeddedEnvironment() as env:
    """
    def __init__(self, initial_time=0):
        self._initial_time = initial_time
        self._startup = []  # type: List[Tuple[Coroutine, float]]
        self._loop = None  # type: Optional[Loop]
        self._scope = EnvironmentScope()

    async def __aenter__(self):
        if self._loop is not None:
            raise RuntimeError('%r is not re-entrant' % self.__class__.__name__)
        self._loop = __LOOP_STATE__.LOOP
        await self._scope.__aenter__()
        if self._loop.time < self._initial_time:
            await (time == self._initial_time)
        for event, delay in self._startup:
            self._schedule(event, delay)
        self._startup.clear()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._scope.__aexit__(exc_type, exc_val, exc_tb)

    async def until(self, until=None):
        """
        Asynchronous version of the ``env.run`` method

        If ``until`` is...

        :py:const:`None`
            The sub-simulation lasts until no more internal events exist.

        an :py:class:`~.Event`
            The sub-simulations last until the event is triggered.
            It is a :py:exc:`RuntimeError` if the event never triggers.

        otherwise
            The sub-simulation last until its time equals ``until``.
        """
        async with self:
            if until is not None:
                if isinstance(until, Event):
                    await until
                else:
                    await (time >= until)
                raise StopSimulation

    def run(self, until=None) -> NoReturn:
        """
        'env.run' is not supported by the 'usim.py' compatibility layer

        An environment cannot be run synchronously. Use instead:
        * 'await env' to run the environment, blocking the current activity
        * 'async with env:' to run both the environment and the current activity

        To run until some time or event, use 'env.until(toe)' instead of 'env'
        """
        raise CompatibilityError(self.run.__doc__)

    def exit(self, value=None) -> NoReturn:
        """
        'env.exit' is not supported by the 'usim.py' compatibility layer

        Use instead:
        * 'return value' inside the process
        """
        raise CompatibilityError(self.exit.__doc__)

    @property
    def now(self):
        if self._loop is None:
            return self._initial_time
        return self._loop.time

    def schedule(self, event: 'Union[Event, Coroutine]', priority=1, delay=0):
        if priority != 1:
            raise NotImplementedError('Only the default priority=1 is supported')
        if isinstance(event, Event):
            event = event.__usimpy_schedule__()
        if delay == 0:
            delay = None
        if self._loop is None:
            self._startup.append((event, delay))
        else:
            self._schedule(event, delay)

    def _schedule(self, coroutine: Coroutine, delay):
        self._scope.do(coroutine, after=delay)

    def process(self, generator: Generator[Event, Event, V]) -> 'Process[V]':
        """Create a new :py:class:`~.Process` for ``generator``"""
        return Process(self, generator)

    def timeout(self, delay, value: Optional[V] = None) -> 'Timeout[V]':
        """Create a new :py:class:`~.Timeout` that triggers after ``delay``"""
        return Timeout(self, delay, value)

    def event(self) -> 'Event':
        return Event(self)

    def all_of(self, events: 'Iterable[Event]') -> 'AllOf':
        return AllOf(self, events)

    def any_of(self, events: 'Iterable[Event]') -> 'AnyOf':
        return AnyOf(self, events)


class Environment(EmbeddedEnvironment):
    def run(self, until=None):
        usim_run(self.until(until))


from .events import Timeout, Process, Event, AnyOf, AllOf
