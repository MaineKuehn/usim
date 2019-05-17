import operator
from weakref import WeakSet

from typing import Callable, Union, Any, Generic, TypeVar, Generator, Awaitable

from .._primitives.notification import postpone
from .._primitives.condition import Condition


#: Type of a (tracked) value
V = TypeVar('V')
#: Right Hand Side type of an operation
RHS = TypeVar('RHS')


class AsyncComparison(Condition):
    """
    An asynchronous comparison of a :py:class:`~.Tracked` value

    This represents expressions of the form ``tracked == 1992``
    or ``tracked_a == tracked_b``. All comparison operators are
    supported. Like any :py:class:`~.Condition`, it can be used both
    in an asynchronous and boolean context.
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
        return AsyncComparison(
            self._left, self._operator_inverse[self._condition], self._right
        )

    def __init__(
            self,
            left: 'Tracked',
            condition: Callable[[Any, Any], bool],
            right: Union[object, 'Tracked']
    ):
        super().__init__()
        self._condition = condition
        self._left = left
        self._right = right
        if isinstance(left, Tracked):
            if isinstance(right, Tracked):
                self._test = lambda: condition(left.value, right.value)
                right.__add_listener__(self)
            else:
                self._test = lambda: condition(left.value, right)
            left.__add_listener__(self)
        else:
            raise TypeError(
                "the left-hand-side in a %s must be of type %s" %
                (self.__class__.__name__, Tracked.__name__)
            )

    def __on_changed__(self):
        if self._test():
            self.__trigger__()

    def __str__(self):
        return '%s %s %s' % (
            self._left, self._operator_symbol[self._condition], self._right
        )

    def __repr__(self):
        return '%s(%r, operator.%s, %r)' % (
            self.__class__.__name__, self._left, self._condition.__name__, self._right
        )


class Tracked(Generic[V]):
    """
    A mutable value whose changes are tracked to generate and trigger events

    The purpose of a tracked value is to derive notification points on the fly.
    Comparison and mathematical expressions define and trigger events, respectively:

    .. code:: python

        async def refill(coffee: Tracked[float]):
            while True:
                # boolean expression providing an event to wait for
                await (coffee < 0.1)
                print('Coffee is low! Initiating emergency refill!')
                # arithmetic expression triggering events of waiters
                await (coffee + 0.9)
                print('Coffee refilled! Emergency resolved!')

    The purpose of :py:class:`~.Tracked` is to make operations asynchronous -
    the actual operations are taken from the wrapped value.
    This dictates both the availability and effect of operations.

    :py:class:`~.Tracked` does not require its underlying ``value`` to be mutable.
    Instead, the underlying ``value`` is replaced when :py:class:`~.Tracked` changes -
    for example, ``await (tracked + 5)`` is a shorthand
    for ``await tracked.set(tracked.value + 5)``.
    This works both for immutable types, such as :py:class:`int`,
    and mutable types, such as :py:class:`list`.

    :py:class:`~.Tracked` assumes sole responsibility for changing ``value``.
    This means that ``value`` should be changed only via :py:meth:`~.set`
    or async operators, such as ``await (tracked + 3)``.
    Circumventing this to change a mutable ``value`` directly prevents
    :py:class:`~.Tracked` from detecting the change and triggering events.
    """
    @property
    def value(self) -> V:
        """The current value"""
        return self._value

    def __init__(self, value: V):
        self._value = value
        self._listeners = WeakSet()  # type: WeakSet[AsyncComparison]

    def __add_listener__(self, listener: AsyncComparison):
        """Add a new listener for changes"""
        self._listeners.add(listener)

    async def set(self, to: V):
        """Set the value"""
        self._value = to
        for listener in list(self._listeners):
            listener.__on_changed__()
        await postpone()

    # boolean operations producing an AsyncComparison
    def __lt__(self, other):
        return AsyncComparison(self, operator.lt, other)

    def __le__(self, other):
        return AsyncComparison(self, operator.le, other)

    def __eq__(self, other):
        return AsyncComparison(self, operator.eq, other)

    def __ne__(self, other):
        return AsyncComparison(self, operator.ne, other)

    def __ge__(self, other):
        return AsyncComparison(self, operator.ge, other)

    def __gt__(self, other):
        return AsyncComparison(self, operator.gt, other)

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
                "Tracked object can't be used in await expression\n"
                "Use a derived condition or expression instead:\n"
                "* 'await (tracked + 2)' to set the value based on its current value\n"
                "* 'await tracked.set(21)' to set the value to a fixed value\n"
                "* 'await (tracked == 21)' to proceed once a value is reached\n"
                "\n"
                "Availability of operators depends on the type of the tracked value."
            )

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._value)


class AsyncOperation(Generic[V, RHS]):
    r"""
    An asynchronous operation on a :py:class:`~.Tracked` value

    This represents expressions of the form ``tracked + 1992``.
    All operators are supported, provided the underlying type supports them.
    The operation is only realised when ``await``\ ed, in which case the
    underlying :py:attr:`~.Tracked.value` is changed.
    """
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
        assert not isinstance(rhs, Tracked),\
            "Operations on Tracked values require one untracked value"
        self._base = base
        self._operator = op
        self._rhs = rhs

    def __await__(self) -> Generator[Any, None, None]:
        base = self._base
        yield from base.set(
            self._operator(base.value, self._rhs)
        ).__await__()

    def __str__(self):
        return '%s %s %s' % (
            self._base, self._operator_symbol[self._operator], self._rhs
        )

    def __repr__(self):
        return '%s(%r, operator.%s, %r)' % (
            self.__class__.__name__, self._base, self._operator.__name__, self._rhs
        )
