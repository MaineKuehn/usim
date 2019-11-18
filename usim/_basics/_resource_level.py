from abc import abstractmethod
from weakref import WeakValueDictionary
from typing import Iterable, Tuple, Type, Generic, TypeVar


T = TypeVar('T')


class ResourceLevels(Generic[T]):
    """
    Common class for named resource levels

    Representation for the levels of multiple named resources. Every set of resources,
    such as :py:class:`usim.Resources` or :py:class:`usim.Capacities`, specializes a
    :py:class:`~.ResourceLevels` subclass with one attribute for each named resource.
    For example, ``Resources(a=3, b=4)`` uses a :py:class:`~.ResourceLevels` with
    attributes ``a`` and ``b``.

    .. code:: python3

        from usim import Resources

        resources = Resources(a=3, b=4)
        print(resources.levels.a)  # 3
        print(resources.levels.b)  # 4
        print(resources.levels.c)  # raises AttributeError

    :py:class:`~.ResourceLevels` subtypes allow no additional attributes other than
    their initial resources, but their values may be changed.
    Instantiating a subtype requires resource levels to be specified by keyword;
    missing resource are set to zero.

    Each resource always uses the same :py:class:`~.ResourceLevels` subtype.
    Binary operators for comparisons and arithmetic can be applied for
    instances of the same subtype.

    .. describe::  levels_a + levels_b
                   levels_a - levels_b

        Elementwise addition/subtraction of values.

    .. describe::  levels_a > levels_b
                   levels_a >= levels_b
                   levels_a <= levels_b
                   levels_a < levels_b

        Strict elementwise comparison of values.
        :py:data:`True` if the comparison is satisfied by each element pair,
        :py:data:`False` otherwise.

    .. describe:: levels_a == levels_b

        Total elementwise equality of values.
        :py:data:`True` if each element pair is equal,
        :py:data:`False` otherwise.
        The inverse of ``levels_a != levels_b``.

    .. describe:: levels_a != levels_b

        Partial elementwise unequality of values.
        :py:data:`False` if each element pair is equal,
        :py:data:`True` otherwise.
        The inverse of ``levels_a == levels_b``.

    In addition, iteration on a :py:class:`~.ResourceLevels` subtype yields
    ``field, value`` pairs. This is similar to :py:meth:`dict.items`.

    .. describe:: for field, value in levels_a

        Iterate over the current ``field, value`` pairs.

    .. describe:: dict(levels_a)

        Create :py:class:`dict` of ``field: value`` pairs.
    """
    __slots__ = ()
    __fields__: Tuple[str] = ()
    #: cache of currently used specialisations to avoid
    #: recreating/duplicating commonly used types
    __specialisation_cache__ = WeakValueDictionary()

    def __init__(self, **kwargs: T):
        spec_name = f'{__specialise__.__module__}.{__specialise__.__qualname__}'
        raise TypeError(
            f'Base class {self.__class__.__name__} cannot be instantiated.\n'
            '\n'
            f'The {self.__class__.__name__} type is intended to be automatically\n'
            'subclassed by resources. You should not encounter the base class during\n'
            'well-behaved simulations.\n'
            '\n'
            f'Use {spec_name} to declare subtypes with valid resource level names.\n'
        )

    @abstractmethod
    def __add__(self, other: 'ResourceLevels[T]') -> 'ResourceLevels[T]':
        raise NotImplementedError

    @abstractmethod
    def __sub__(self, other: 'ResourceLevels[T]') -> 'ResourceLevels[T]':
        raise NotImplementedError

    @abstractmethod
    def __gt__(self, other: 'ResourceLevels[T]') -> bool:
        raise NotImplementedError

    @abstractmethod
    def __ge__(self, other: 'ResourceLevels[T]') -> bool:
        raise NotImplementedError

    @abstractmethod
    def __le__(self, other: 'ResourceLevels[T]') -> bool:
        raise NotImplementedError

    @abstractmethod
    def __lt__(self, other: 'ResourceLevels[T]') -> bool:
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other: 'ResourceLevels[T]') -> bool:
        raise NotImplementedError

    @abstractmethod
    def __ne__(self, other: 'ResourceLevels[T]') -> bool:
        raise NotImplementedError

    def __iter__(self):
        for field in self.__fields__:
            yield field, getattr(self, field)

    def __repr__(self):
        content = ', '.join(
            f'{key}={item}' for key, item in self
        )
        return f'{self.__class__.__name__}({content})'


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
