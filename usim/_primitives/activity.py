from functools import wraps
from typing import Coroutine, TypeVar, Generic, Optional, Tuple, Any, List

from .._core.loop import __LOOP_STATE__, Interrupt
from .condition import Condition


RT = TypeVar('RT')


class CancelActivity(Interrupt):
    ...


class Activity(Condition, Generic[RT]):
    """
    Active coroutine that allows others to listen for its completion

    :note: Simulation code should never instantiate this class directly.
    """
    __slots__ = ('payload', 'context', '_result', '_execution', '_cancellations')

    def __init__(self, payload: Coroutine[Any, Any, RT], context):
        @wraps(payload)
        async def payload_wrapper():
            if self._cancellations:
                self._result = None, self._cancellations[0]
            else:
                try:
                    result = await self.payload
                except CancelActivity as err:
                    self._result = None, err
                else:
                    self._result = result, None
            for cancellation in self._cancellations:
                cancellation.revoke()
            self.__trigger__()
        super().__init__()
        self._cancellations = []  # type: List[CancelActivity]
        self._result = None  # type: Optional[Tuple[RT, BaseException]]
        self.payload = payload
        self.context = context
        self._execution = payload_wrapper()

    @property
    async def result(self) -> RT:
        """
        Wait for the completion of this :py:class:`Activity` and return its result

        :returns: the result of the activity
        :raises: :py:exc:`CancelActivity` if the activity was cancelled
        """
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

    def __runner__(self):
        return self._execution

    def __close__(self):
        """Close the underlying coroutine"""
        if self._result is None:
            self._execution.close()
            self._result = None, GeneratorExit()

    def cancel(self, *token) -> None:
        """Cancel this activity during the current time step"""
        if self._result is None:
            cancellation = CancelActivity('cancel activity', id(self), 'for', *token)
            self._cancellations.append(cancellation)
            cancellation.scheduled = True
            __LOOP_STATE__.LOOP.schedule(self._execution, signal=cancellation)

    def __repr__(self):
        return '<%s of %s [%s] (%s)>' % (
            self.__class__.__name__, self.payload,
            self.context,
            'outstanding' if not self else (
                'result={!r}'.format(self._result[0])
                if self._result[1] is None
                else
                'signal={!r}'.format(self._result[1])
            ),
        )


class NotDone(Condition):
    def __init__(self, activity: Activity):
        super().__init__()
        self.activity = activity

    def __bool__(self):
        return not self.activity

    def __invert__(self):
        return self.activity

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, self.activity)
