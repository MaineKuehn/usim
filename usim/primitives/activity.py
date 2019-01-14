from typing import Coroutine, TypeVar, Generic, Optional, Tuple, Any

from ..core import GetTask, Schedule
from .notification import Broadcast
from .condition import Condition


RT = TypeVar('RT')


class CancelActivity(BaseException):
    ...


class Activity(Broadcast, Condition, Generic[RT]):
    """
    Active coroutine that allows others to listen for its completion

    :note: Simulation code should never instantiate this class directly.
    """
    __slots__ = ('payload', '_result')

    def __init__(self, payload: Coroutine[Any, Any, RT]):
        super().__init__()
        self.payload = payload
        self._result = None  # type: Optional[Tuple[RT, BaseException]]

    @property
    async def result(self) -> RT:
        await self
        result, error = self._result
        if error is not None:
            raise error
        else:
            return result

    def __bool__(self):
        return self._result is not None

    def __invert__(self):
        return NotDone(self)

    async def __runner__(self):
        try:
            result = await self.payload
        except CancelActivity as err:
            self._result = None, err
        else:
            self._result = result, None
        await self.__trigger__()

    async def cancel(self):
        """
        Cancel this activity, preventing further actions

        :note: If an activity cancels itself,
               :py:exc:`CancelActivity` is raised immediately.
        """
        if self._result is not None:
            if await GetTask() is self.payload:
                raise CancelActivity()
            else:
                await Schedule(self.payload, signal=CancelActivity())

    def __repr__(self):
        return '<%s of %s (%s)>' % (
            self.__class__.__name__, self.payload,
            'outstanding' if not self else (
                'result={!r}'.format(self._result[0])
                if self._result[1] is None
                else
                'signal={!r}'.format(self._result[1])
            ),
        )


class NotDone(Broadcast, Condition):
    def __init__(self, activity: Activity):
        super().__init__()
        self.activity = activity

    def __bool__(self):
        return not self.activity

    def __invert__(self):
        return self.activity

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, self.activity)
