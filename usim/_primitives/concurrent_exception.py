from typing import Optional, Tuple, Union, Type, Dict, Any


class MetaConcurrent(type):
    def __new__(
            mcs,
            name: str,
            bases: Tuple[Type, ...],
            namespace: Dict[str, Any],
            specialisations: Optional[Tuple[Union[Type[Exception], 'ellipsis'], ...]] = None,
            **kwargs,
    ):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)  # type: MetaConcurrent
        if specialisations is not None:
            try:
                i = specialisations.index(...)
            except ValueError:
                cls.inclusive = False
            else:
                cls.inclusive = True
                specialisations = specialisations[:i] + specialisations[i+1:]
                assert ... not in specialisations,\
                    "only one ... allowed in specialisations"
        else:
            cls.inclusive = True
        cls.specialisations = specialisations
        return cls

    # Implementation Note:
    # The Python data model defines both
    # * ``isinstance(a, b) => type(b).__instancecheck__(b, a)``
    # * ``issubclass(a, b) => type(b).__subclasscheck__(b, a)``
    # So we could need either for error handling.
    #
    # The Python language translates the except clause of
    #   try: raise a
    #   except b as err: <block>
    # to ``if issubclass(type(a), b): <block>``.
    # Which means we need ``__subclasscheck__`` only.
    def __instancecheck__(cls, instance):
        if type(instance) == Concurrent:
            # except MultiError:
            if cls.specialisations is None:
                return True
            # except MultiError[]:
            else:
                return cls._instancecheck_specialisation(instance)
        return False

    def __subclasscheck__(cls, subclass):
        return super().__subclasscheck__(subclass)

    def _instancecheck_specialisation(cls, instance: 'Concurrent'):
        matched_specialisations = sum(
            1 for specialisation in cls.specialisations
            if any(
                isinstance(child, specialisation)
                for child in instance.children
            )
        )
        if matched_specialisations < len(cls.specialisations):
            return False
        # except MultiError[KeyError, ...]
        elif cls.inclusive:
            return True
        # except MultiError[KeyError]:
        else:
            return not any(
                not isinstance(child, cls.specialisations)
                for child in instance.children
            )

    def __getitem__(cls, item: Union[Type[Exception], 'ellipsis', Tuple[Union[Type[Exception], 'ellipsis'], ...]]):
        if cls.specialisations is not None:
            raise TypeError(f'Cannot specialise already specialised {cls.__name__!r}')
        if not isinstance(item, tuple):
            if item is ...:
                return cls
            assert issubclass(item, Exception),\
                f'{cls.__name__!r} may only be specialised by Exception subclasses'
            name = f'{cls.__name__}[{item.__name__}]'
            return MetaConcurrent(name, (cls,), {}, specialisations=(item,))
        else:
            assert all(
                issubclass(child, Exception) or (child is ...) for child in item
            ),\
                f'{cls.__name__!r} may only be specialised by Exception subclasses'
            name = f'{cls.__name__}[{", ".join(child.__name__ for child in item)}]'
            return MetaConcurrent(name, (cls,), {}, specialisations=tuple(set(item)))


class Concurrent(Exception, metaclass=MetaConcurrent):
    """
    Exception from one or more concurrent :term:`activity`

    A meta-exception that represents any :py:exc:`Exception` of any failing
    :py:class:`~usim.typing.Task` of a :py:class:`~usim.Scope`. This does not
    include any :py:exc:`Exception` thrown in the body of the scope. As a result,
    it is possible to separately catch concurrent and regular exceptions:

    .. code:: python3

        try:
            async with Scope() as scope:
                if random.random() < 0.5:
                    scope.do(
                        async_raise(RuntimeError('concurrent'))
                    )
                else:
                    raise RuntimeError('scoped')
        except RuntimeError:
            print('Failed in body')
        except Concurrent:
            print('Failed in child')

    In addition to separating concurrent and regular exceptions,
    :py:class:`~.Concurrent` can also separate different concurrent exception types.
    Subscribing the :py:class:`~.Concurrent` type as ``Concurrent[Exception]``
    specialise ``except`` clauses to a specific concurrent :py:exc:`Exception`:

    .. code:: python3

        try:
            async with Scope() as scope:
                if random.random() < 0.333:
                    scope.do(async_raise(KeyError('concurrent')))
                elif random.random() < 0.5:
                    scope.do(async_raise(IndexError('concurrent')))
                else:
                    scope.do(async_raise(ValueError('concurrent')))
        except Concurrent[KeyError]:
            print('Failed key lookup')
        except Concurrent[IndexError]:
            print('Failed indexing')
        except (Concurrent[TypeError], Concurrent[ValueError]):
            print('Incorrect type/value of something!')

    Since a :py:class:`~usim.Scope` can run more than one :py:class:`~usim.typing.Task`
    concurrently, there can be more than one failure as well. Subscribing
    :py:class:`~.Concurrent` is possible for several types at once:
    ``Concurrent[ExceptionA, ExceptionB]`` matches only ``ExceptionA`` and
    ``ExceptionB`` at the same time, and
    ``Concurrent[ExceptionA, ExceptionB, ...]`` matches at least ``ExceptionA`` and
    ``ExceptionB`` at the same time.

    .. code:: python3

        try:
            async with Scope() as scope:
                scope.do(async_raise(KeyError('concurrent')))
                if random.random() < 0.5:
                    scope.do(async_raise(IndexError('concurrent')))
                if random.random() < 0.5:
                    scope.do(async_raise(ValueError('concurrent')))
        except Concurrent[KeyError]:
            print('Failed only key lookup')
        except Concurrent[KeyError, IndexError]:
            print('Failed key lookup and indexing')
        except Concurrent[KeyError, ...]:
            print('Failed key lookup and something else')

    """
    def __init__(self, *children):
        super().__init__(children)
        self.children = children

    def __str__(self):
        return ', '.join(map(repr, self.children))

    def __repr__(self):
        return f'<usim.f{self.__class__.__name__} of {self}>'
