from typing import Optional, List, Tuple, Coroutine, Generator, TypeVar, Iterable,\
    Union
from .._core.loop import __LOOP_STATE__, Loop, ActivityError
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

    This environment can be constructed in any ``usim`` :term:`Activity`.
    It exposes most of the :py:class:`simpy.Environment` interface, with
    the exception of :py:meth:`simpy.Environment.run`. To avoid errors,
    the environment must be run in a context.

    .. code:: python3

        def car(env):
            while True:
                print('Start parking at %s' % env.now)
                yield env.timeout(5)
                print('Start driving at %s' % env.now)
                yield env.timeout(2)

        async def legacy_simulation():
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
        However, you can have an arbitrary number of :term:`Activity`
        running concurrently.

    Migrating to ``usim``
    ---------------------

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
        Use ``await (time + delay)``, or one of its variant such
        as ``await (time == deadline)``.

    **creating an event** (:py:meth:`~.event`)
        Create a new :py:class:`usim.Flag`, and ``await flag`` to be notified
        once it is :py:meth:`~usim.Flag.set`.

    **combining events** (:py:meth:`~.all_of` and :py:meth:`~.any_of`)
        Use the operators ``|`` ("any"), ``&`` ("all") or ``~`` ("not") to
        combine events, as in ``flag1 & flag2 | ~flag3``.
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
        """Asynchronous version of the :py:meth:`~.run` method"""
        async with self:
            if until is not None:
                if isinstance(until, Event):
                    await until
                else:
                    if until <= time.now:
                        raise ValueError('until must be in the future')
                    await (time >= until)
                raise StopSimulation

    def run(
        self, until: 'Union[None, float, Event[V]]' = None
    ) -> Union[None, V, Exception]:
        """
        Run the simulation of this environment synchronously

        If ``until`` is...

        :py:const:`None`
            The sub-simulation lasts until no more internal events exist.

        an :py:class:`~.Event`
            The sub-simulations last until the event is triggered.
            It is a :py:exc:`RuntimeError` if the event never triggers.

        otherwise
            The sub-simulation last until its time equals ``until``.
        """
        try:
            # test whether we are contained in an active usim loop
            __LOOP_STATE__.LOOP.time
        except RuntimeError:
            try:
                usim_run(self.until(until))
            except ActivityError as err:
                # unwrap any exceptions
                raise err.__cause__
            else:
                if isinstance(until, Event):
                    return until.value
        else:
            raise CompatibilityError(
                "'env.run' is not supported inside a 'usim' simulation\n"
                "\n"
                "Synchronous running blocks the event loop. Use instead\n"
                "* 'await env.until()' to block only the current activity\n"
                "* 'async with env:' to concurrently run the environment\n"
                "\n"
                "You can 'env.run' outside of a 'usim' simulation"
            )

    def exit(self, value=None):
        """
        'env.exit' is not supported by the 'usim.py' compatibility layer

        Use instead:
        * 'return value' inside the process
        """
        raise CompatibilityError(self.exit.__doc__)

    @property
    def now(self) -> float:
        """
        The current time of the simulation

        .. hint::

            Migrate by using ``usim.time.now`` instead.
        """
        if self._loop is None:
            return self._initial_time
        return self._loop.time

    def schedule(self, event: 'Union[Event, Coroutine]', priority=1, delay=0):
        """
        Schedule a :py:class:`~.Event` to be triggered after ``delay``

        .. note::

            Setting the parameter ``priority`` is not supported.

        .. hint::

            Events of ``usim`` are not scheduled but directly triggered,
            for example :py:meth:`usim.Flag.set`.
        """
        if priority != 1:
            raise CompatibilityError('Only the default priority=1 is supported')
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
        Create a new :py:class:`~.AllOf` that triggers on each ``events``

        .. hint::

            Migrate by combining :py:class:`usim.typing.Condition`
            using ``|`` instead, e.g. ``flag1 | flag2``.
        """
        return AnyOf(self, events)


from .events import Timeout, Process, Event, AnyOf, AllOf  # noqa: E402
