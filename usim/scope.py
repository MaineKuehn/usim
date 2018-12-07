from typing import List, Union, Coroutine, TypeVar, Awaitable

from .core import Task, Resumption, Schedule, GetTime, GetTask

#: Yield Type of a Coroutine
YT = TypeVar('YT')
#: Send Type of a Coroutine
ST = TypeVar('ST')
#: Return Type of a Coroutine
RT = TypeVar('RT')


class CancelScope(object):
    """
    Scope that cancels all children on exit

    .. code:: python

        with CancelScope() as scope:
            await scope.fork(time(10))
            await scope.fork(time(random.randint(5, 15)))
        print(time())
    """
    def __init__(self):
        self.children = []  # type: List[Union[Task, Resumption]]
        self._task = None  # type: Task

    def __enter__(self):
        raise RuntimeError("%s must be used in 'async with'" % self.__class__.__name__)

    async def fork(self, coroutine: Coroutine[YT, ST, RT], after: float = None, *, at: float = None) -> Awaitable[RT]:
        if after is at is None:
            schedule = await Schedule(Task(coroutine))
        elif after is not None:
            assert after is None or at is None, "only one of 'after' or 'at' may be used"
            schedule = await Schedule(Task(coroutine), delay=after)
        else:
            schedule = await Schedule(Task(coroutine), delay=(at - await GetTime()))
        self.children.append(schedule)
        self.children.append(schedule.target)
        return schedule.target

    async def __aenter__(self):
        assert self._task is None, '%s is not re-entrant' % self.__class__.__name__
        self._task = await GetTask()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._task = None
        for child in self.children:
            await child.cancel()
        return False
