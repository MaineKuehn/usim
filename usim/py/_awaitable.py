from typing import Awaitable, TypeVar, Generic, Optional, Tuple
from .. import Flag, until


R = TypeVar('R')


class AwaitableEvent(Generic[R]):
    """
    Wraps an Awaitable as a SimPy :py:class:`~usim.py.events.Event`

    This type only exists for internal usage to allow a
    :py:class:`~usim.py.events.Process` to ``yield`` a :py:class:`~.Notification`
    or :term:`activity`.
    It is not intended for manual instantiation and does not provide the ``Event``
    interface beyond what is needed internally.

    If you encounter a :py:class:`~.NotificationEvent` during a simulation,
    **this is a bug**; please report it in our
    `Issue Tracker <https://github.com/MaineKuehn/usim/issues>`_.
    """
    @property
    def value(self) -> R:
        try:
            value, exception = self._value
        except TypeError:
            raise AttributeError(
                f"{self.__class__.__name__!r} object has no attribute 'value' set yet"
            )
        else:
            return value if exception is None else exception

    @property
    def ok(self) -> bool:
        return self._value is not None and self._value[1] is None

    def __init__(self, awaitable: Awaitable[R]):
        self._awaitable = awaitable
        self._value = None  # type: Optional[Tuple[Optional[R], Optional[Exception]]]
        #: usim exceptions are always handled
        self.defused = True

    async def wait_interruptible(self, interrupted: Flag) -> bool:
        """
        Wait for the notification to trigger or the process being ``interrupted``

        Returns ``True`` if the notification triggered or
        ``False`` if an interrupt occured first.
        """
        async with until(interrupted):
            try:
                result = await self._awaitable
            except Exception as err:
                self._value = None, err
                return True
            else:
                self._value = result, None
                return True
        return False
