Concurrent Activities and Exceptions
====================================

.. container:: left-col

    In complex simulations, it is inevitable that things go wrong sometimes
    - in some cases, failure is even an expected part of the simulation itself.
    This makes it important to make failures explicit,
    but also to have tools to handle them.

    μSim extends the normal Python Exception model with two additions:
    A :py:class:`~usim.Scope` can perform multiple actions at once,
    and thus may encounter several failures at once.
    Similarly, several :py:exc:`~usim.Concurrent` exceptions may need to
    be handled individually or all at once.

Concurrency and Exceptions
--------------------------

.. content-tabs:: left-col

    The purpose of a :py:class:`~usim.Scope` is to :py:meth:`~usim.Scope.do`
    activities concurrently, alongside a main activity represented
    by the Scope body itself.
    Consequently, we can separate exceptions into synchronous exceptions in the body,
    or :py:exc:`~usim.Concurrent` exceptions in a child activity.

.. container:: content-tabs right-col

    .. rubric:: Demo that randomly fails in the body or child of a Scope

    .. code:: python3

        async def araise(what: BaseException):
            raise what

        async def scope_exception_demo():
            async with Scope() as scope:
                delay = random.random()
                scope.do(
                    araise(RuntimeError('child')),  # A: concurrent exception
                    after=delay
                )
                await (time + 1 - delay)
                raise RuntimeError('body')          # B: synchronous exception

.. content-tabs:: left-col

    Any exception that happens synchronously in the body is a failure of the
    :py:class:`~usim.Scope` itself.
    In the example, the ``RuntimeError('body')`` will teardown the scope and
    then propagate onwards.

    Any exception that happens concurrently in a child is a failure of the
    payloads, not the :py:class:`~usim.Scope`.
    In the example, the ``RuntimeError('child')`` will cause the
    :py:class:`~usim.Scope` to shut down and re-raise the exception as a
    ``Concurrent(RuntimeError('child'))``.

Handling Concurrent Exceptions
------------------------------

.. content-tabs:: left-col

    The :py:exc:`~usim.Concurrent` exception model is made to integrate with
    Python's regular ``try``/``except`` exception handling machinery.
    Synchronous exceptions do not need any extra effort to handle.
    The :py:exc:`~usim.Concurrent` exceptions have the required, additional
    error handling built in.
    To handle a :py:exc:`~usim.Concurrent` exception of a specific type,
    use ``except Concurrent[ExceptionType]`` instead of ``except ExceptionType``.

.. content-tabs:: right-col

    .. rubric:: Demo for handling concurrent/synchronous exceptions

    .. code:: python3

        async def handle_exception_demo()
            try:
                await scope_exception_demo()
            except RuntimeError as err:
                print('Handled synchronous exception:', err)
            except Concurrent[RuntimeError] as err:
                print('Handled concurrent exception:', err)

.. content-tabs:: left-col

    μSim guarantees that you never have to handle both a regular and a
    :py:exc:`~usim.Concurrent` exception at the same time - it is an "either or" situation.
    Consequently, you can safely use separate error handlers for either exception flavour.
    :py:exc:`~usim.Concurrent` exceptions follow the regular subclassing relations
    of exceptions -- for example, ``Concurrent[LookupError]`` matches both
    ``Concurrent[KeyError]`` and ``Concurrent[IndexError]``.

.. content-tabs:: right-col

    .. note::

        μSim considers the use of a :py:class:`~usim.Scope` an implementation detail of
        functions and abstractions that should *not* be visible to users.
        Consequently, we handle any :py:exc:`~usim.Concurrent` exception internally
        and only propagate regular exceptions.
        While this is not enforced for custom functions and abstractions,
        we strongly recommend to adhere to this convention.

Concurrency Privileges
^^^^^^^^^^^^^^^^^^^^^^

.. content-tabs:: left-col

    μSim itself is a highly concurrent, exception driven library.
    This means that certain exceptions must propagate unobstructed,
    while others are suppressed at well-defined points.
    In order not to require users to manually adhere to such unwritten rules,
    μSim has a concept for exception privileges in concurrent situations.

    Task local exceptions
        Python's :py:exc:`GeneratorExit` and μSim's internal ``Interrupt``
        represent the teardown of a Task or parts of it.
        In the Task they belong to, these exceptions will replace all
        other synchronous or concurrent exceptions; otherwise, they are suppressed.
        As a result, you do not have to worry about re-raising an ``Interrupt`` and
        you should never encounter a ``Concurrent[GeneratorExit]``, for example.

    Application global exceptions
        Python's :py:exc:`SystemExit`, :py:exc:`KeyboardInterrupt`, and
        :py:exc:`AssertionError` [#debug]_ represent the teardown of the entire simulation.
        These exceptions supersede any synchronous and concurrent exceptions,
        and are always propagated as regular, synchronous exceptions.

    As a result, μSim will do the correct thing by default.
    You only have to worry about μSim's internal exceptions if you use catch-all
    exception handlers such as ``except BaseException:`` or even ``except:``.
    In case you are unsure, ``raise`` at the end of a handler to let exceptions propagate.

Handling Multiple Exceptions
----------------------------

.. content-tabs:: left-col

    Concurrency means that *several* child tasks may fail at the same :term:`time`.
    As a result, a :py:exc:`~usim.Concurrent` exception may contain several failures
    at once.

.. content-tabs:: right-col

    .. rubric:: Demo that fails in multiple children of a Scope

    .. code:: python3

        async def multi_exception_demo():
            async with Scope() as scope:
                scope.do(araise(IndexError('A')))    # A
                scope.do(araise(KeyError('B')))      # B
                scope.do(araise(IndexError('C')))    # C
                await (time + 2)                     # async exceptions arrive here
                scope.do(araise(KeyError('D')))      # D

.. content-tabs:: left-col

    This example will propagate a single exception :py:exc:`~usim.Concurrent` exception
    containing ``IndexError('A')``, ``KeyError('B')``, and ``IndexError('C')`` --
    the ``KeyError('D')`` is suppressed by the scope stopping itself and its children.
    The *type* of the exception includes all types of its child exceptions,
    namely ``Concurrent[IndexError, KeyError]``.
    Note that neither the *number* nor *order* of exceptions is captured in the type.

    Use ``[]`` to specialise precisely which concurrent failure you want to handle.
    Multiple subtypes represent an "and" relation -- ``Concurrent[X, Y]`` requires
    both ``X`` and ``Y`` exceptions to be thrown at the same time.
    Including a literal ``...`` means that additional subtypes are allowed --
    ``Concurrent[X, Y, ...]`` matches both ``X`` and ``Y`` plus zero or more others.
    Use ``Concurrent[...]`` to handle any concurrent exception.

.. content-tabs:: right-col

    .. rubric:: Specializing concurrent exceptions

    .. code:: python3

        try:
            await some_failure()
        except X:
            print('Handled a synchronous X exception')
        except Y, Concurrent[Y]:
            print('Handled a synchronous or concurrent Y exception')
        except Concurrent[X, Z]:
            print('Handled a concurrent X and Z exception')
        except Concurrent[X], Concurrent[Z]:
            print('Handled a concurrent X or a concurrent Z exception')

.. content-tabs:: left-col

    As with exception handling in general, avoid too broad exception cases.
    Prefer specific exceptions over general ones,
    e.g. ``Concurrent[KeyError]`` over ``Concurrent[LookupError]``
    or even ``Concurrent[Exception]``.
    If possible, use exact exception subtypes over open ones,
    e.g. ``Concurrent[KeyError, RuntimeError]`` instead of ``Concurrent[KeyError, ...]``.
    Finally, we recommend using ``Concurrent[...]`` only if you want to suppress
    concurrent exceptions unconditionally.

Propagating Exceptions Best-Practices
-------------------------------------

.. content-tabs:: left-col

    Whether an :term:`activity` uses concurrency or not is usually not obvious.
    Unless explicitly documented, a :py:exc:`~usim.Concurrent` exception propagating
    out of an :term:`activity` is likely unexpected.
    As such, avoid propagating :py:exc:`~usim.Concurrent` exceptions whenever possible!

    All abstractions in μSim convert internal :py:exc:`~usim.Concurrent` exceptions
    to regular exceptions.
    Only :py:class:`~usim.Scope` and derived types may raise
    :py:exc:`~usim.Concurrent` exceptions when exiting an ``async with`` context.
    The intention is to hide implementation details,
    while allowing full control on expected concurrency.

    We strongly recommend to similarly avoid propagating
    :py:exc:`~usim.Concurrent` exceptions if possible.
    When unavoidable, do not expose nested concurrency but
    propagate a :py:meth:`~usim.Concurrent.flattened` exception.


    .. [#debug] For the use of :py:exc:`AssertionError` by μSim,
                see also :doc:`./debug`.
