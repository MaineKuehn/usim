from typing import Optional, Tuple, Union, Type, Dict, Any, ClassVar
from weakref import WeakValueDictionary


class MetaConcurrent(type):
    """
    Metaclass to implement specialisation of :py:exc:`Concurrent`

    Provides specialisation via subscription and corresponding type checks:
    ``Type[spec]`` and ``issubclass(Type[spec], Type[spec, spec2])``. Accepts
    the specialisation ``...`` (:py:const:`Ellipsis`) to mark the specialisation
    as inclusive, meaning a subtype may have additional specialisations.
    """
    inclusive: bool
    specialisations: Optional[Tuple[Type[Exception]]]
    template: 'MetaConcurrent'

    def __new__(
        mcs,
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        specialisations:
            Optional[Tuple[Union[Type[Exception], 'ellipsis'], ...]] = None,
        **kwargs,
    ):
        cls = super().__new__(
            mcs, name, bases, namespace, **kwargs
        )  # type: MetaConcurrent
        if specialisations is not None:
            try:
                i = specialisations.index(...)
            except ValueError:
                inclusive = False
            else:
                inclusive = True
                specialisations = specialisations[:i] + specialisations[(i + 1):]
                assert ... not in specialisations,\
                    "only one ... allowed in specialisations"
            template = bases[0]
        else:
            inclusive = True
            template = cls
        cls.inclusive = inclusive
        cls.specialisations = specialisations
        cls.template = template
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
        """``isinstance(instance, cls)``"""
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        """``issubclass(subclass, cls)``"""
        try:
            template = subclass.template
        except AttributeError:
            return False
        else:
            # if we are templated, check that the specialisation matches
            if template == cls.template:
                # except MultiError:
                if cls.specialisations is None:
                    return True
                # except MultiError[]:
                else:
                    return cls._subclasscheck_specialisation(subclass)
            return False

    def _subclasscheck_specialisation(cls, subclass: 'MetaConcurrent'):
        """``issubclass(Type[subclass.specialisation], Type[cls.specialisation])``"""
        matched_specialisations = sum(
            1 for specialisation in cls.specialisations
            if any(
                issubclass(child, specialisation)
                for child in subclass.specialisations
            )
        )
        if matched_specialisations < len(cls.specialisations):
            return False
        # except MultiError[KeyError, ...]
        elif cls.inclusive:
            # We do not care if ``subclass`` has unmatched specialisations
            return True
        # except MultiError[KeyError]:
        else:
            # Make sure that ``subclass`` has no unmatched specialisations
            return not any(
                not issubclass(child, cls.specialisations)
                for child in subclass.specialisations
            )

    def __getitem__(
        cls,
        item:
            Union[
                Type[Exception],
                'ellipsis',
                Tuple[Union[Type[Exception], 'ellipsis'], ...]
            ]
    ):
        """``cls[item]``"""
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
                (child is ...) or issubclass(child, Exception) for child in item
            ),\
                f'{cls.__name__!r} may only be specialised by Exception subclasses'
            spec = ", ".join(
                '...' if child is ... else child.__name__ for child in item
            )
            name = f'{cls.__name__}[{spec}]'
            return MetaConcurrent(name, (cls,), {}, specialisations=tuple(set(item)))

    def __repr__(cls):
        return f"<class 'usim.{cls.__name__}'>"


class Concurrent(Exception, metaclass=MetaConcurrent):
    """
    Exception from one or more concurrent :term:`activity`

    A meta-exception that represents any :py:exc:`Exception` of any failing
    :py:class:`~usim.typing.Task` of a :py:class:`~usim.Scope`. This does not
    include any :py:exc:`Exception` thrown in the body of the scope. As a result,
    it is possible to separately handle concurrent and regular exceptions:

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
    specialises ``except`` clauses to a specific concurrent :py:exc:`Exception`:

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

    Note that
    ``except (Concurrent[A], Concurrent[B]:`` means *either* ``A`` *or* ``B``
    whereas
    ``except Concurrent[A, B]:`` means *both* ``A`` *and* ``B``.
    """
    __specialisations__ = WeakValueDictionary()
    #: Whether this type accepts additional unmatched specialisations
    inclusive: ClassVar[bool]
    #: Specialisations this type expects in order to match
    specialisations: ClassVar[Optional[Tuple[Type[Exception]]]]
    #: Basic template of specialisation
    template: ClassVar[MetaConcurrent]

    def __new__(cls: 'Type[Concurrent]', *children):
        if not children:
            assert cls.specialisations is None,\
                f"specialisation {cls.specialisations} does not match"\
                f" children {children}; Note: Do not 'raise {cls.__name__}'"
            return super().__new__(cls)
        specialisations = frozenset(type(child) for child in children)
        try:
            special_cls = cls.__specialisations__[children]
        except KeyError:
            special_cls = cls[tuple(specialisations)]
            cls.__specialisations__[specialisations] = special_cls
        self = super().__new__(special_cls)
        return self

    def __init__(self, *children):
        super().__init__(children)
        self.children = children

    def __str__(self):
        return \
            f'{self.__class__.__name__}: {", ".join(map(repr, self.children))}'

    def __repr__(self):
        return \
            f'<object usim.{self.__class__.__name__} '\
            f'of {", ".join(map(repr, self.children))}>'
