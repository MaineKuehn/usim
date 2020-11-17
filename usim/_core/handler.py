r"""
Generic loop effect handler

This is the core implementation allowing simulation objects to
have "effects" – e.g. trigger activities or read the time.
"""
from typing_extensions import Protocol, Coroutine
import threading
import contextlib


class AbstractLoop(Protocol):
    #: The currently running activity
    activity: Coroutine
    #: The current time of the simulation
    time: float


class MissingLoop:
    r"""
    Placeholder for the :py:class:`~.Loop` expected in an active simulation

    This class exists to provide helpful error messages if usim is used
    without starting its event loop. If you encounter this class unexpectedly,
    see 'https://usim.readthedocs.io' for usage details.
    """
    __slots__ = ("_entry_point",)
    activity: Coroutine
    time: float

    def __init__(self, entry_point: str = "usim.run"):
        self._entry_point = entry_point

    def __getattr__(self, field: str):
        raise RuntimeError(
            (
                "field '%s' can only be accessed with an active usim event loop\n\n"
                "You have attempted to use an async feature of usim outside of\n"
                "a usim simulation. This likely means that you used a different\n"
                "async framework. You must run usim's async features as part of\n"
                "an active usim simulation.\n\n"
                "Use '%s' to start an appropriate simulation."
            )
            % (field, self._entry_point)
        )

    def __repr__(self):
        return "{self.__class__.__name__}(entry_point={self._entry_point})".format(
            self=self,
        )


class LoopState(threading.local):
    loop: AbstractLoop

    @property
    def LOOP(self):
        return self.loop

    def __init__(self):
        self.loop = MissingLoop()

    @contextlib.contextmanager
    def assign(self, loop: AbstractLoop):
        outer_loop, self.loop = self.loop, loop
        try:
            yield
        finally:
            self.loop = outer_loop


__LOOP_STATE__ = LoopState()
