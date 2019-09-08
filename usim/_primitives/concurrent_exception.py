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
    # metaclass instance fields - i.e. class fields
    # used to define specialisations of a base type
    inclusive: bool
    specialisations: Optional[Tuple[Type[Exception]]]
    template: 'MetaConcurrent'
    __specialisations__: WeakValueDictionary

    # Called when constructing a class (an instance of the metaclass)
    # The following corresponds to calling __new__:
    #
    # class name(*bases, specialisations=specialisations, inclusive=inclusive):
    #   <namespace>
    #
    # __new__ is called once per type hierarchy when the template
    # is defined using `class ...`.
    # Afterwards, __getitem__ (i.e. Class[...]) explicitly calls
    # __new__ to create specialisations.
    def __new__(
        mcs,
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        specialisations:
            Optional[Tuple[Type[Exception], ...]] = None,
        inclusive: bool = True,
        **kwargs,
    ):
        cls = super().__new__(
            mcs, name, bases, namespace, **kwargs
        )  # type: MetaConcurrent
        if specialisations is not None:
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
    #
    # Which means we need just ``__subclasscheck__`` for error handling.
    # We implement ``__instancecheck__`` for consistency only.
    def __instancecheck__(cls, instance):
        """``isinstance(instance, cls)``"""
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        """``issubclass(subclass, cls)``"""
        # issubclass(A, A)
        if cls is subclass:
            return True
        try:
            template = subclass.template
        except AttributeError:
            return False
        else:
            # if we are templated, check that the specialisation matches
            # the superclass specialisation must be at least
            # as general as the subclass specialisation
            if template == cls.template:
                # except MultiError:
                # issubclass(A[???], A)
                # the base class is the superclass of all its specialisations
                if cls.specialisations is None:
                    return True
                # except MultiError[]:
                # issubclass(A[???], A[???])
                else:
                    return cls._subclasscheck_specialisation(subclass)
            return False

    def _subclasscheck_specialisation(cls, subclass: 'MetaConcurrent'):
        """``issubclass(:Type[subclass.specialisation], Type[:cls.specialisation])``"""
        # specialisations are covariant - if A <: B, then Class[A] <: Class[B]
        #
        # This means that we must handle cases where specialisations
        # match multiple times - for example, when matching
        # Class[B] against Class[A, B], then B matches both A and B,
        #
        # Make sure that ``cls`` has no unmatched specialisations
        matched_specialisations = all(
            any(
                issubclass(child, specialisation)
                for child in subclass.specialisations
            ) for specialisation in cls.specialisations
        )
        if not matched_specialisations:
            return False
        # except MultiError[KeyError, ...]
        elif cls.inclusive:
            # We do not care if ``subclass`` has unmatched specialisations
            return True
        # except MultiError[KeyError]:
        else:
            # Make sure that ``subclass`` has no unmatched specialisations
            #
            # We need to check every child of subclass instead of comparing counts.
            # This is needed in case that we have duplicate matches. Consider:
            # Concurrent[KeyError, LookupError], Concurrent[KeyError, RuntimeError]
            return not any(
                not issubclass(child, cls.specialisations)
                for child in subclass.specialisations
            )

    # Specialisation Interface
    # Allows to do ``Cls[A, B, C]`` to specialise ``Cls`` with ``A, B, C``.
    # This part is the only one that actually understands ``...``.
    #
    # Expect this to be called by user-facing code, either directly or as a result
    # of ``Cls(A(), B(), C())``. Errors should be reported appropriately.
    #
    # Unlike () calls, [] calls only take a single argument.
    # Multiple arguments get passed as a tuple:
    # - Cls[a]      means   Cls.__getitem__(a)
    # - Cls[a, b]   means   Cls.__getitem__((a, b))
    def __getitem__(
        cls,
        item:  # [Exception] or [...] or [Exception, ...]
            Union[
                Type[Exception],
                'ellipsis',
                Tuple[Union[Type[Exception], 'ellipsis'], ...]
            ]
    ):
        """``cls[item]`` - used to specialise ``cls`` with ``item``"""
        # validate/normalize parameters
        #
        # Cls[A, B][C]
        if cls.specialisations is not None:
            raise TypeError(f'Cannot specialise already specialised {cls.__name__!r}')
        # Cls[...]
        if item is ...:
            return cls
        # Cls[item]
        elif type(item) is not tuple:
            assert issubclass(item, Exception),\
                f'{cls.__name__!r} may only be specialised by Exception subclasses'
            item = (item,)
        # Cls[item1, item2]
        else:
            assert all(
                (child is ...) or issubclass(child, Exception) for child in item
            ),\
                f'{cls.__name__!r} may only be specialised by Exception subclasses'
        return cls._get_specialisation(item)

    def _get_specialisation(cls, item):
        # provide specialised class
        #
        # If a type already exists for the given specialisation, we return that
        # same type. This avoids class creation and allows fast `A is B` checks.
        #
        # Each template stores the currently used __specialisations__, indexed
        # by a set of items - this eliminates duplicates and ordering as well.
        unique_spec = frozenset(item)
        try:
            specialised_cls = cls.__specialisations__[unique_spec]
        except KeyError:
            inclusive = ... in unique_spec
            specialisations = tuple(child for child in unique_spec if child is not ...)
            spec = ", ".join(  # the specialisation string "KeyError, IndexError, ..."
                child.__name__ for child in specialisations
            ) + (', ...' if inclusive else '')
            # class 'cls.__name__[spec]'(cls, specialisations, inclusive):
            #   pass
            #
            # Note: type(name, bases, namespace) parameters cannot be passed by keyword
            specialised_cls = MetaConcurrent(
                f'{cls.__name__}[{spec}]', (cls,), {},
                specialisations=specialisations, inclusive=inclusive
            )
            cls.__specialisations__[unique_spec] = specialised_cls
        return specialised_cls

    def __repr__(cls):
        return f"<class 'usim.{cls.__name__}'>"


class Concurrent(BaseException, metaclass=MetaConcurrent):
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
    concurrently, there can be more than one exception as well. Subscribing
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
    # currently used specialised subclasses
    __specialisations__ = WeakValueDictionary()
    #: Whether this type accepts additional unmatched specialisations
    inclusive: ClassVar[bool]
    #: Specialisations this type expects in order to match
    specialisations: ClassVar[Optional[Tuple[Type[Exception], ...]]]
    #: Basic template of specialisation
    template: ClassVar[MetaConcurrent]
    #: Exceptions that occurred concurrently
    children: Tuple[Exception, ...]

    # __new__ automatically specialises Concurrent to match its children.
    # Concurrent(A(), B()) => Concurrent[A, B](A(), B())
    def __new__(cls: 'Type[Concurrent]', *children: Exception):
        if not children:
            assert cls.specialisations is None,\
                f"specialisation {cls.specialisations} does not match"\
                f" children {children}; Note: Do not 'raise {cls.__name__}'"
            return super().__new__(cls)
        special_cls = cls[tuple(type(child) for child in children)]
        return super().__new__(special_cls)

    def __init__(self, *children: Exception):
        super().__init__(children)
        self.children = children

    def __str__(self):
        return \
            f'{self.__class__.__name__}: {", ".join(map(repr, self.children))}'

    def __repr__(self):
        return \
            f'<object usim.{self.__class__.__name__} '\
            f'of {", ".join(map(repr, self.children))}>'
