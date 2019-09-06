from abc import abstractmethod
from weakref import WeakValueDictionary
from typing import Iterable, Tuple, Type, Generic, TypeVar


T = TypeVar('T')


class ResourceLevels(Generic[T]):
    """Base class for named resource levels"""
    __slots__ = ()
    __fields__ = ()  # type: Tuple[str]
    #: cache of currently used specialisations to avoid
    #: recreating/duplicating commonly used types
    __specialisation_cache__ = WeakValueDictionary()
    #: instance of this specialisation
    #: with all values as zero
    zero = None  # type: ResourceLevels

    def __init__(self, **kwargs: T):
        raise TypeError(
            'Base class %r cannot be instantiated.' % self.__class__.__name__
            + 'Use %s.%s to declare subtypes with valid resource level names.' % (
                __specialise__.__module__, __specialise__.__name__
            )
        )

    @abstractmethod
    def __add__(self, other: 'ResourceLevels[T]') -> 'ResourceLevels[T]':
        pass

    @abstractmethod
    def __sub__(self, other: 'ResourceLevels[T]') -> 'ResourceLevels[T]':
        pass

    @abstractmethod
    def __gt__(self, other: 'ResourceLevels[T]') -> bool:
        pass

    @abstractmethod
    def __ge__(self, other: 'ResourceLevels[T]') -> bool:
        pass

    @abstractmethod
    def __le__(self, other: 'ResourceLevels[T]') -> bool:
        pass

    @abstractmethod
    def __lt__(self, other: 'ResourceLevels[T]') -> bool:
        pass

    @abstractmethod
    def __eq__(self, other: 'ResourceLevels[T]') -> bool:
        pass

    @abstractmethod
    def __ne__(self, other: 'ResourceLevels[T]') -> bool:
        pass

    def __iter__(self):
        for field in self.__fields__:
            yield field, getattr(self, field)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join(
                '%s=%s' % (name, getattr(self, name))
                for name in self.__fields__
            )
        )


def __specialise__(zero: T, names: Iterable[str]) -> Type[ResourceLevels[T]]:
    """
    Create a specialisation of :py:class:`~.ResourceLevels`

    :param zero: zero value for all fields
    :param names: names of fields
    """
    fields = tuple(sorted(names))
    try:
        return ResourceLevels.__specialisation_cache__[fields]
    except KeyError:
        pass

    class SpecialisedResourceLevels(ResourceLevels):
        __slots__ = fields
        __fields__ = fields

        __init__ = __make_init__(zero, fields)

        __add__ = __binary_op__('__add__', '+', fields)
        __sub__ = __binary_op__('__sub__', '-', fields)

        __gt__ = __comparison_op__('__gt__', '>', fields)
        __ge__ = __comparison_op__('__ge__', '>=', fields)
        __le__ = __comparison_op__('__le__', '<=', fields)
        __lt__ = __comparison_op__('__le__', '<', fields)
        __eq__ = __comparison_op__('__eq__', '==', fields)

        def __ne__(self, other):
            return not self == other

    SpecialisedResourceLevels.zero = SpecialisedResourceLevels(
        **dict.fromkeys(fields, zero)
    )
    ResourceLevels.__specialisation_cache__[fields] = SpecialisedResourceLevels
    return SpecialisedResourceLevels


def __make_init__(zero, names: Tuple[str, ...]):
    """Make an ``__init__`` with ``names`` as keywords and defaults of ``zero``"""
    namespace = {}
    args_list = f'={zero}, '.join(names)
    exec(
        '\n'.join(
            [
                f"""def __init__(self, *, {args_list}={zero}):"""
            ] + [
                f"""    self.{name} = {name}"""
                for name in names
            ]
        ),
        namespace
    )
    return namespace['__init__']


def __binary_op__(op_name: str, op_symbol: str, names: Tuple[str, ...]):
    """
    Make an operator method ``op_name`` to apply ``op_symbol`` to all fields ``names``

    .. code:: python3

        __add__ = __make_binary_op__("__add__", '+', ('foo', 'bar'))

        def __add__(self, other):
            return type(self)(
                foo = self.foo + other.foo,
                bar = self.bar + other.bar,
            )
    """
    namespace = {}
    exec(
        '\n'.join(
            [
                f"""def {op_name}(self, other):""",
                """    assert type(self) is type(other),\\""",
                """        'resource levels specialisations cannot be mixed'""",
                """    return type(self)(""",
            ] + [
                f"""        {name} = self.{name} {op_symbol} other.{name},"""
                for name in names
            ] + [
                """           )"""
            ]
        ),
        namespace
    )
    return namespace[op_name]


def __comparison_op__(op_name: str, op_symbol: str, names: Tuple[str]):
    """
    Make a comparison method ``op_name`` to apply ``op_symbol`` to all fields ``names``

    .. code:: python3

        __eq__ = __make_binary_op__("__eq__", '==', ('foo', 'bar'))

        def __add__(self, other):
            return (
                self.foo + other.foo
                and self.bar + other.bar
            )
    """
    namespace = {}
    exec(
        '\n'.join(
            [
                f"""def {op_name}(self, other):""",
                """    assert type(self) is type(other),\\""",
                """        'resource levels specialisations cannot be mixed'""",
                """    return (""",
                f"""        self.{names[0]} {op_symbol} other.{names[0]}"""
            ] + [
                f"""        and self.{name} {op_symbol} other.{name}"""
                for name in names[1:]
            ] + [
                """           )"""
            ]
        ),
        namespace
    )
    return namespace[op_name]
