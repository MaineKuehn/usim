"""
This module provides the :py:class:`~usim.py.core.Environment`,
which hosts any SimPy simulation. In order to create new events,
components of the simulation need access to the current environment
- it is common to pass this as the parameter ``env``.

An environment can be run standalone, or embedded into a μSim simulation.
The latter allows interactions between the μSim and SimPy components.
"""
from typing import Optional, List, Tuple, Coroutine, Generator, TypeVar, Iterable,\
    Union
from .._core.loop import __LOOP_STATE__, Loop
from .. import time, run as usim_run, Concurrent
from .. import Scope

from .events import Event
from .exceptions import NotCompatibleError, StopSimulation, StopProcess


class EnvironmentScope(Scope):
    def _is_suppressed(self, exc_val):
        return isinstance(exc_val, StopSimulation) or super()._is_suppressed(exc_val)

    PROMOTE_CONCURRENT = Scope.PROMOTE_CONCURRENT + (StopSimulation,)


def _inside_usim():
    """Whether the current stack is run by ``usim``"""
    try:
        __LOOP_STATE__.LOOP.time
    except RuntimeError:
        return False
    else:
        return True


V = TypeVar('V')


class Environment:
    r"""
    SimPy Environment compatibility layer embedded in a μSim simulation

    This environment can be run by itself or in any μSim :term:`Activity`.
    It exposes most of the :py:class:`simpy.Environment` interface, skipping
    methods meant for internal usage such as :py:meth:`simpy.Environment.step`.
    To avoid errors, the :py:meth:`~.run` method can be used only *outside*
    a μSim simulation. Use the environment as an ``async with`` context
    or ``await env.until()`` to run it *inside* a μSim simulation.

    .. code:: python3

        def car(env):
            while True:
                print('Start parking at %s' % env.now)
                yield env.timeout(5)
                print('Start driving at %s' % env.now)
                yield env.timeout(2)

        async def wrapped_simulation():
            async with Environment() as env:
                env.process(car(env))

    In order to run until a point in time or event, use :py:meth:`~.until`.

    .. code:: python3

        async def legacy_simulation():
            env = Environment()
            env.process(car(env))
            await env.until(15)

    .. warning:

        Unlike a :py:class:`simpy.Environment`, this environment
        *cannot* resume after running ``until`` some point.
        However, you can have an arbitrary number of :term:`Activity`\ s
        running concurrently.

    .. hint::

        **Migrating to μSim**

        There is no explicit environment in ``usim``;
        its functionality is split across several types, and
        the event loop spawned by :py:func:`usim.run` is implicitly available.

        **starting a simulation**
            Call :py:func:`usim.run` with an initial set of activities.

        **spawning new processes** (:py:meth:`~.process`)
            Open a :py:class:`usim.Scope` which can :py:meth:`~.usim.Scope.do`
            several activities at once.
            An opened :py:class:`~usim.Scope` can be passed to other activities,
            similar to an environment.

        **timeout after a delay** (:py:meth:`~.timeout`)
            Use ``await (time + delay)``, or one of its variants such
            as ``await (time == deadline)``.

        **creating an event** (:py:meth:`~.event`)
            Create a new :py:class:`usim.Flag`, and ``await flag`` to be notified
            once it is :py:meth:`~usim.Flag.set`.

        **combining events** (:py:meth:`~.all_of` and :py:meth:`~.any_of`)
            Use the operators ``|`` ("any"), ``&`` ("all") or ``~`` ("not") to
            combine events, as in ``flag1 & flag2 | ~flag3``.
    """
    __slots__ = '_initial_time', '_startup', '_loop', '_scope', 'active_process'

    def __init__(self, initial_time=0):
        self._initial_time = initial_time
        self._startup = []  # type: List[Tuple[Coroutine, float]]
        self._loop = None  # type: Optional[Loop]
        self._scope = EnvironmentScope()
        #: The currently active process
        self.active_process = None  # type: Optional[Process]

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
        """Asynchronous version of the :py:meth:`~.run` method"""
        try:
            async with self:
                if until is not None:
                    if isinstance(until, Event):
                        await until.__usimpy_flag__
                    else:
                        if until < time.now:
                            raise ValueError('until must be in the future')
                        await (time >= until)
                    raise StopSimulation
        except Concurrent as err:
            raise err.children[0]
        except StopSimulation:
            pass

    def run(
        self, until: 'Union[None, float, Event[V]]' = None
    ) -> Union[None, V, Exception]:
        """
        Run the simulation of this environment synchronously

        If ``until`` is...

        :py:const:`None`
            The sub-simulation lasts until no more internal events exist.

        an :py:class:`~.Event`
            The sub-simulation lasts until the event is triggered.
            It is a :py:exc:`RuntimeError` if the event never triggers.

        otherwise
            The sub-simulation lasts until simulation time equals ``until``.
        """
        if not _inside_usim():
            usim_run(self.until(until))
            if isinstance(until, Event):
                if until.triggered:
                    return until.value
                raise RuntimeError("'until' event was not triggered")
        else:
            raise NotCompatibleError(
                "'env.run' is not supported inside a 'usim' simulation\n"
                "\n"
                "Synchronous 'run' blocks the event loop. Use instead:\n"
                "* 'await env.until()' to block only the current activity\n"
                "* 'async with env:' to concurrently run the environment\n"
                "\n"
                "You may 'env.run' outside of a 'usim' simulation"
            )

    def exit(self, value=None):
        """
        Stop the current process, optionally providing a ``value``

        .. warning::

            This method exists for historical compatibility only.
            Use ``return value`` instead.
        """
        raise StopProcess(value)

    def step(self):
        """
        'Environment.step' is not implemented by the μSim compatibility layer

        The μSim compatibility layer uses the regular μSim event loop.
        There is no public alternative to 'Environment.step'.
        """
        raise NotCompatibleError(self.step.__doc__)

    def peek(self):
        """
        'Environment.peek' is not implemented by the μSim compatibility layer

        The μSim compatibility layer uses the regular μSim event loop.
        There is no public alternative to 'Environment.peek'.
        """
        raise NotCompatibleError(self.step.__doc__)

    @property
    def now(self) -> float:
        """
        Current time of the simulation

        .. hint::

            Migrate by using :py:attr:`usim.time.now` instead.
        """
        if self._loop is None:
            return self._initial_time
        return self._loop.time

    def schedule(self, event: 'Union[Event, Coroutine]', priority=1, delay=0):
        """
        Schedule an :py:class:`~.Event` to be triggered after ``delay``

        Setting the parameter ``priority`` to anything but the default
        is not supported. It only exists for compatibility with the
        :py:mod:`simpy` API.

        .. hint::

            Events of ``usim`` are not scheduled but directly triggered,
            for example :py:meth:`usim.Flag.set`.
        """
        if priority != 1:
            raise NotCompatibleError('Only the default priority=1 is supported')
        if isinstance(event, Event):
            event = event.__usimpy_schedule__()
        if delay == 0:
            delay = None
        # We may get called before the loop has started.
        # Queue events until the loop starts.
        if self._loop is None:
            self._startup.append((event, delay))
        else:
            self._schedule(event, delay)

    def _schedule(self, coroutine: Coroutine, delay):
        self._scope.do(coroutine, after=delay)

    def process(self, generator: Generator[Event, Event, V]) -> 'Process[V]':
        """
        Create a new :py:class:`~.Process` for ``generator``

        .. hint::

            Migrate by using a :py:class:`usim.Scope` and its
            :py:meth:`~.usim.Scope.do` method instead.
        """
        return Process(self, generator)

    def timeout(self, delay, value: Optional[V] = None) -> 'Timeout[V]':
        """
        Create a new :py:class:`~.Timeout` that triggers after ``delay``

        .. hint::

            Migrate by using :py:data:`usim.time`, e.g.
            as ``await (time + delay)`` or ``await (time == deadline)``.
        """
        return Timeout(self, delay, value)

    def event(self) -> 'Event':
        """
        Create a new :py:class:`~.Event` that can be manually triggered

        .. hint::

            Migrate by using :py:class:`usim.Flag` instead.
        """
        return Event(self)

    def all_of(self, events: 'Iterable[Event]') -> 'AllOf':
        """
        Create a new :py:class:`~.AllOf` that triggers on all ``events``

        .. hint::

            Migrate by combining :py:class:`usim.typing.Condition`
            using ``&`` instead, e.g. ``flag1 & flag2``.
        """
        return AllOf(self, events)

    def any_of(self, events: 'Iterable[Event]') -> 'AnyOf':
        """
        Create a new :py:class:`~.AnyOf` that triggers on the first of ``events``

        .. hint::

            Migrate by combining :py:class:`usim.typing.Condition`
            using ``|`` instead, e.g. ``flag1 | flag2``.
        """
        return AnyOf(self, events)

    def __del__(self):
        # simpy requires us to register callback handlers
        # on instantiation or success. This can happen even
        # though the event loop is never run.
        # Clean up our internal callbacks to avoid resource
        # leak warnings.
        for event, _ in self._startup:
            event.close()


from .events import Timeout, Process, Event, AnyOf, AllOf  # noqa: E402
