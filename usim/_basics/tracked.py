import operator

from typing import Callable, List, Union, Any, Generic, TypeVar, Coroutine, Generator,\
    Awaitable

from .._core.loop import Interrupt as CoreInterrupt
from .._primitives.notification import postpone
from .._primitives.condition import Condition


#: Type of a (tracked) value
V = TypeVar('V')
#: Right Hand Side type of an operation
RHS = TypeVar('RHS')


class BoolExpression(Condition):
    """
    A boolean condition on a Tracked value
    """
    _operator_symbol = {
        operator.lt: '<',
        operator.le: '<=',
        operator.eq: '==',
        operator.ne: '!=',
        operator.ge: '>=',
        operator.gt: '>',
    }
    _operator_inverse = {
        operator.lt: operator.ge,
        operator.ge: operator.lt,
        operator.gt: operator.le,
        operator.le: operator.gt,
        operator.eq: operator.ne,
        operator.ne: operator.eq,
    }

    def __bool__(self):
        return self._test()

    def __invert__(self):
        return BoolExpression(
            self._operator_inverse[self._condition], self._left, self._right
        )

    def __init__(
            self,
            condition: Callable[[Any, Any], bool],
            left: Union[object, 'Tracked'],
            right: Union[object, 'Tracked']
    ):
        super().__init__()
        self._subscribed = False
        self._condition = condition
        self._left = left
        self._right = right
        self._source = tuple(
            value for value in (left, right) if isinstance(value, Tracked)
        )
        if isinstance(left, Tracked) and isinstance(right, Tracked):
            self._test = lambda: condition(left.value, right.value)
        elif isinstance(left, Tracked):
            self._test = lambda: condition(left.value, right)
        elif isinstance(right, Tracked):
            self._test = lambda: condition(left, right.value)
        else:
            raise TypeError(
                "at least one of 'left' or 'right' must be of type %s" %
                Tracked.__name__
            )

    def _start_listening(self):
        if not self._subscribed:
            for source in self._source:
                source.__add_listener__(self)
        self._subscribed = True

    def _stop_listening(self):
        if self._subscribed and not self._waiting:
            if self._subscribed:
                for source in self._source:
                    source.__del_listener__(self)
        self._subscribed = False

    def __await__(self) -> Generator[Any, None, bool]:
        self._start_listening()
        result = (yield from super().__await__())
        self._stop_listening()
        return result  # noqa: B901

    def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._start_listening()
        super().__subscribe__(waiter, interrupt)

    def __trigger__(self):
        super().__trigger__()
        self._stop_listening()

    async def __on_changed__(self):
        if self._test():
            await self.__trigger__()

    def __repr__(self):
        return '%s %s %s' % (
            self._left, self._operator_symbol[self._condition], self._right
        )


class Tracked(Generic[V]):
    """
    A value whose changes are tracked to generate events

    The purpose of a tracked value is to derive notification points on the fly.
    Boolean and arithmetic expressions provide events and triggers, respectively:

    .. code:: python

        async def refill(coffee: Tracked[float]):
            while True:
                # boolean expression providing an event to wait for
                await (coffee < 0.1)
                print('Coffee is low! Initiating emergency refill!')
                # arithmetic expression triggering waiting activities
                await (coffee + 0.9)
                print('Coffee refilled! Emergency resolved!')
    """
    @property
    def value(self) -> V:
        return self._value

    def __init__(self, value: V):
        self._value = value
        self._listeners = []  # type: List[BoolExpression]

    def __add_listener__(self, listener: BoolExpression):
        """Add a new listener for changes"""
        self._listeners.append(listener)

    def __del_listener__(self, listener: BoolExpression):
        """Remove an existing listener for changes"""
        self._listeners.remove(listener)

    async def set(self, to: V):
        """Set the value"""
        self._value = to
        for listener in self._listeners:
            await listener.__on_changed__()
        await postpone()

    # boolean operations producing a BoolExpression
    def __lt__(self, other):
        return BoolExpression(operator.lt, self, other)

    def __le__(self, other):
        return BoolExpression(operator.le, self, other)

    def __eq__(self, other):
        return BoolExpression(operator.eq, self, other)

    def __ne__(self, other):
        return BoolExpression(operator.ne, self, other)

    def __ge__(self, other):
        return BoolExpression(operator.ge, self, other)

    def __gt__(self, other):
        return BoolExpression(operator.gt, self, other)

    # modifying operators
    def __add__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__add__, other)

    def __sub__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__sub__, other)

    def __mul__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__mul__, other)

    def __matmul__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__matmul__, other)

    def __truediv__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__truediv__, other)

    def __floordiv__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__floordiv__, other)

    def __mod__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__mod__, other)

    def __pow__(self, power, modulo=None) -> 'Union[AsyncOperation[V], Awaitable]':
        if modulo is None:
            return AsyncOperation(self, operator.__pow__, power)
        return self.set(pow(self.value, power, modulo))

    def __lshift__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__lshift__, other)

    def __rshift__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__rshift__, other)

    def __and__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__and__, other)

    def __or__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__or__, other)

    def __xor__(self, other) -> 'AsyncOperation[V]':
        return AsyncOperation(self, operator.__xor__, other)

    def __radd__(self, other):
        raise TypeError(
            "tracked object does not support reflected operators\n"
            "Use 'await (tracked + 4)' instead of 'await (4 + tracked)'"
        )

    __rsub__ = __rmul__ = __rmatmul__ = __rtruediv__ = __rfloordiv__ = __rmod__\
        = __rdivmod__ = __rpow__ = __rlshift__ = __rrshift__ = __rand__ = __rxor__\
        = __ror__ = __radd__

    # augmented operators
    # Python currently does not support await for augmented assignment, as in
    #       await a += 20
    def __iadd__(self, other):
        raise TypeError("tracked object does not support augmented assignment\n"
                        "Use 'tracked = await (tracked + 4)' instead")

    __isub__ = __imul__ = __imatmul__ = __itruediv__ = __ifloordiv__ = __imod__\
        = __ipow__ = __ilshift__ = __irshift__ = __iand__ = __ixor__ = __ior__\
        = __iadd__

    def __bool__(self):
        raise TypeError(
            "tracked object has no bool()\n"
            "Use 'bool(tracked.value)' or 'await (tracked == True)' instead"
        )

    if __debug__:
        def __await__(self):
            raise TypeError(
                "tracked object can't be used in await expression\n"
                "Use a derived condition or expression instead"
            )

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._value)


class AsyncOperation(Generic[V, RHS]):
    __slots__ = ('_base', '_operator', '_rhs')

    _operator_symbol = {
        operator.add: '+',
        operator.sub: '-',
        operator.mul: '*',
        operator.matmul: '@',
        operator.truediv: '/',
        operator.floordiv: '//',
        operator.mod: '%',
        operator.pow: '**',
        operator.lshift: '<<',
        operator.rshift: '>>',
        operator.and_: '&',
        operator.or_: '|'
    }

    def __init__(self, base: Tracked[V], op: Callable[[V, RHS], V], rhs: RHS):
        self._base = base
        self._operator = op
        self._rhs = rhs

    def __await__(self) -> Generator[Any, None, None]:
        base = self._base
        yield from base.set(
            self._operator(base.value, self._rhs)
        ).__await__()

    def __str__(self):
        return '%s %s' % (self._operator_symbol[self._operator], self._rhs)

    def __repr__(self):
        return '%s(%s, %r)' % (self.__class__.__name__, self._operator, self._rhs)
