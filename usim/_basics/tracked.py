import operator

from typing import Callable, List, Union, Any, Generic, TypeVar, Coroutine, Awaitable

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
        return BoolExpression(self._operator_inverse[self._condition], self._left, self._right)

    def __init__(self, condition: Callable[[Any, Any], bool], left: Union[object, 'Tracked'], right: Union[object, 'Tracked']):
        super().__init__()
        self._subscribed = False
        self._condition = condition
        self._left = left
        self._right = right
        self._source = tuple(value for value in (left, right) if isinstance(value, Tracked))
        if isinstance(left, Tracked) and isinstance(right, Tracked):
            self._test = lambda: condition(left.value, right.value)
        elif isinstance(left, Tracked):
            self._test = lambda: condition(left.value, right)
        elif isinstance(right, Tracked):
            self._test = lambda: condition(left, right.value)
        else:
            raise TypeError("at least one of 'left' or 'right' must be of type %s" % Tracked.__name__)

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

    def __await__(self) -> Awaitable[bool]:
        self._start_listening()
        result = (yield from super().__await__())
        self._stop_listening()
        return result

    async def __subscribe__(self, waiter: Coroutine, interrupt: CoreInterrupt):
        self._start_listening()
        await super().__subscribe__(waiter, interrupt)

    async def __trigger__(self):
        await super().__trigger__()
        self._stop_listening()

    async def __on_changed__(self):
        if self._test():
            await self.__trigger__()

    def __repr__(self):
        return '%s %s %s' % (self._left, self._operator_symbol[self._condition], self._right)


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

    async def __set_expression__(self, to: V):
        await self.set(to)
        return self

    def _async_operation(self, op: Callable[[V, RHS], V], rhs: RHS) -> 'TrackedOperation[V]':
        return TrackedOperation(self, Operation(op, rhs))

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
        return BoolExpression(operator.gt, self, other)

    def __gt__(self, other):
        return BoolExpression(operator.ge, self, other)

    # modifying operators
    def __add__(self, other):
        return self.__set_expression__(self.value + other)

    def __sub__(self, other):
        return self.__set_expression__(self.value - other)

    def __mul__(self, other):
        return self.__set_expression__(self.value * other)

    def __matmul__(self, other):
        return self.__set_expression__(self.value @ other)

    def __truediv__(self, other):
        return self.__set_expression__(self.value / other)

    def __floordiv__(self, other):
        return self.__set_expression__(self.value // other)

    def __mod__(self, other):
        return self.__set_expression__(self.value % other)

    def __divmod__(self, other):
        return self.__set_expression__(divmod(self.value, other))

    def __pow__(self, power, modulo=None):
        return self.__set_expression__(pow(self.value, power, modulo))

    def __lshift__(self, other):
        return self.__set_expression__(self.value << other)

    def __rshift__(self, other):
        return self.__set_expression__(self.value >> other)

    def __and__(self, other):
        return self.__set_expression__(self.value & other)

    def __or__(self, other):
        return self.__set_expression__(self.value | other)

    def __radd__(self, other):
        raise TypeError("tracked object does not support reflected operators\n"
                        "Use 'await (tracked + 4)' instead of 'await (4 + tracked)'")

    __rsub__ = __rmul__ = __rmatmul__ = __rtruediv__ = __rfloordiv__ = __rmod__ = __rdivmod__ = __rpow__ = __rlshift__ \
        = __rrshift__ = __rand__ = __rxor__ = __ror__ = __radd__

    # augmented operators
    # Python currently does not support await for augmented assignment, as in
    #       await a += 20
    def __iadd__(self, other):
        raise TypeError("tracked object does not support augmented assignment\n"
                        "Use 'tracked = await (tracked + 4)' instead")

    __isub__ = __imul__ = __imatmul__ = __itruediv__ = __ifloordiv__ = __imod__ = __ipow__ = __ilshift__ = __irshift__ \
        = __iand__ = __ixor__ = __ior__ = __iadd__

    def __await__(self):
        raise TypeError("tracked object can't be used in await expression\n"
                        "Use a derived condition or expression instead")

    def __bool__(self):
        raise TypeError("tracked object has no bool()\n"
                        "Use 'bool(tracked.value)' or 'await (tracked == True)' instead")

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._value)


class Operation(Generic[V, RHS]):
    __slots__ = ('operator', 'rhs')
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

    def __init__(self, op: Callable[[V, RHS], V], rhs: RHS):
        self.operator = op
        self.rhs = rhs

    def __str__(self):
        return '%s %s' % (self._operator_symbol[self.operator], self.rhs)

    def __repr__(self):
        return '%s(%s, %r)' % (self.__class__.__name__, self.operator, self.rhs)


class TrackedOperation(Generic[V]):
    __slots__ = ('_tracked', '_operations')

    def __init__(self, value: Tracked[V], *operations: Operation):
        self._tracked = value
        self._operations = operations

    def __await__(self) -> Tracked[V]:
        tracked = self._tracked
        for operation in self._operations:
            yield from tracked.set(operation.operator(tracked.value, operation.rhs))
        return tracked

    def __extend__(self, op: Callable[[V, RHS], V], rhs: RHS) -> 'TrackedOperation[V]':
        return TrackedOperation(self._tracked, *self._operations, Operation(op, rhs))

    # modifying operators
    def __add__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.add, other)

    def __sub__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.sub, other)

    def __mul__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.mul, other)

    def __matmul__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.matmul, other)

    def __truediv__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.truediv, other)

    def __floordiv__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.floordiv, other)

    def __mod__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.mod, other)

    def __pow__(self, other: RHS, modulo=None) -> 'TrackedOperation[V]':
        if modulo is not None:
            raise TypeError("%s does not support the 'modulo' parameter for 'pow'" % self.__class__.__name__)
        return self.__extend__(operator.pow, other)

    def __lshift__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.lshift, other)

    def __rshift__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.rshift, other)

    def __and__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.and_, other)

    def __or__(self, other: RHS) -> 'TrackedOperation[V]':
        return self.__extend__(operator.or_, other)

    def __radd__(self, other):
        raise TypeError("tracked object does not support reflected operators\n"
                        "Use 'await (tracked + 4 + 5)' instead of 'await (4 + tracked + 5)'")

    __rsub__ = __rmul__ = __rmatmul__ = __rtruediv__ = __rfloordiv__ = __rmod__ = __rdivmod__ = __rpow__ = __rlshift__ \
        = __rrshift__ = __rand__ = __rxor__ = __ror__ = __radd__

    def __str__(self):
        return '%s %s %s)' % (
            '(' * len(self._operations),
            self._tracked,
            ') '.join(str(op) for op in self._operations)
        )

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            str(self._operations)[1:-1]
        )
