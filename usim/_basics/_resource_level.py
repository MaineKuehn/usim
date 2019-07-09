from abc import ABC, abstractmethod
from weakref import WeakValueDictionary
from typing import Iterable, Optional, Tuple, Type


class ResourceLevels(ABC):
    """Base class for resource levels"""
    __slots__ = ()
    __fields__ = None  # type: Optional[Tuple[str]]
    __specialisation_cache__ = WeakValueDictionary()
    zero = None  # type: ResourceLevels

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def __add__(self, other: 'ResourceLevels') -> 'ResourceLevels':
        pass

    @abstractmethod
    def __sub__(self, other: 'ResourceLevels') -> 'ResourceLevels':
        pass

    @abstractmethod
    def __gt__(self, other: 'ResourceLevels') -> bool:
        pass

    @abstractmethod
    def __ge__(self, other: 'ResourceLevels') -> bool:
        pass

    @abstractmethod
    def __le__(self, other: 'ResourceLevels') -> bool:
        pass

    @abstractmethod
    def __lt__(self, other: 'ResourceLevels') -> bool:
        pass

    @abstractmethod
    def __eq__(self, other: 'ResourceLevels') -> bool:
        pass

    @abstractmethod
    def __ne__(self, other: 'ResourceLevels') -> bool:
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


def __specialise__(zero, names: Iterable[str]) -> Type[ResourceLevels]:
    fields = tuple(sorted(names))
    if not fields:
        return ResourceLevels
    try:
        return ResourceLevels.__specialisation_cache__[fields]
    except KeyError:
        pass

    class SpecialisedResourceLevels(ResourceLevels):
        __slots__ = fields
        __fields__ = fields

        __init__ = __make_init__(zero, fields)

        __add__ = __make_bin_op__('__add__', '+', fields)
        __sub__ = __make_bin_op__('__sub__', '-', fields)

        __gt__ = __make_comp__('__gt__', '>', fields)
        __ge__ = __make_comp__('__ge__', '>=', fields)
        __le__ = __make_comp__('__le__', '<=', fields)
        __lt__ = __make_comp__('__le__', '<', fields)
        __eq__ = __make_comp__('__le__', '==', fields)

        def __ne__(self, other):
            return not self == other

    SpecialisedResourceLevels.zero = SpecialisedResourceLevels(
        **dict.fromkeys(fields, zero)
    )
    ResourceLevels.__specialisation_cache__[fields] = SpecialisedResourceLevels
    return SpecialisedResourceLevels


def __make_init__(zero, names: Tuple[str]):
    namespace = {}
    exec(
        '\n'.join(
            [
                """def __init__(self, *, {args_list}={zero}):""".format(
                    args_list='={}, '.format(zero).join(names),
                    zero=zero,
                )
            ] + [
                """    self.{name} = {name}""".format(name=name)
                for name in names
            ]
        ),
        namespace
    )
    return namespace['__init__']


def __make_bin_op__(op_name: str, op_symbol: str, names: Tuple[str]):
    namespace = {}
    exec(
        '\n'.join(
            [
                """def {op_name}(self, other):""".format(
                    op_name=op_name
                ),
                """    assert type(self) is type(other),\\""",
                """        'resource levels specialisations cannot be mixed'""",
                """    return type(self)(""",
            ] + [
                """        {name} = self.{name} {op_symbol} other.{name},""".format(
                    op_symbol=op_symbol,
                    name=name,
                )
                for name in names
            ] + [
                """           )"""
            ]
        ),
        namespace
    )
    return namespace[op_name]


def __make_comp__(op_name: str, op_symbol: str, names: Tuple[str]):
    namespace = {}
    exec(
        '\n'.join(
            [
                """def {op_name}(self, other):""".format(
                    op_name=op_name
                ),
                """    assert type(self) is type(other),\\""",
                """        'resource levels specialisations cannot be mixed'""",
                """    return (""",
                """        self.{name} {op_symbol} other.{name}""".format(
                    op_symbol=op_symbol,
                    name=names[0],
                )
            ] + [
                """        and self.{name} {op_symbol} other.{name}""".format(
                    op_symbol=op_symbol,
                    name=name,
                )
                for name in names[1:]
            ] + [
                """           )"""
            ]
        ),
        namespace
    )
    return namespace[op_name]