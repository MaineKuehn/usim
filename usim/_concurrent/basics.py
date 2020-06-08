from typing import Coroutine, Any, TypeVar, Awaitable, AsyncIterator, Optional, List

from .._primitives.context import Scope
from .._basics.streams import Queue

import asyncstdlib as a

RT = TypeVar('RT')


async def _race_monitor(contestant: Awaitable[RT], queue: Queue):
    result = await contestant
    await queue.put(result)


async def race(
    *activities: Coroutine[Any, Any, RT],
    winners: Optional[int] = None,
) -> AsyncIterator[RT]:
    """
    Run all ``activities`` concurrently to get the first ``winners`` results available

    :param activities: activities to run concurrently
    :param winners: maximum number of results
    :return: async iterable of results
    :raises usim.Concurrent: if any of the ``activities`` raise an exception

    If there are more results than ``winners``,
    any remaining ``activities`` are aborted after yielding the last result.
    If there are less results than ``winners``,
    the iterator finishes after yielding the last result.
    If ``winners`` is :py:data:`None`, the iterator provides all results.

    Results are always yielded in the order of becoming available.
    The initial order of ``activities`` is irrelevant.
    """
    results: Queue[RT] = Queue()
    winners = winners if winners is not None else len(activities)
    async with Scope() as scope:
        for activity in activities:
            scope.do(
                _race_monitor(activity, queue=results),
                volatile=True,
            )
        async for winner in a.islice(results, winners):
            yield winner


async def collect(*activities: Coroutine[Any, Any, RT]) -> List[RT]:
    """
    Run all ``activities`` concurrently to provide all results

    :param activities: activities to run concurrently
    :return: list of results
    :raises usim.Concurrent: if any of the ``activities`` raise an exception

    Results are always yielded in the order of the ``activities`` producing them;
    the order at which individual ``activities`` finish is irrelevant.
    However, results are only available after all ``activities`` are finished.
    """
    async with Scope() as scope:
        tasks = [scope.do(activity) for activity in activities]
    return [await task for task in tasks]
