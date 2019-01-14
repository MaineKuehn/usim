import operator

from typing import Callable, List, Union, Any, Generic, TypeVar, Coroutine

from ..core import Interrupt as CoreInterrupt
from .notification import Broadcast, postpone
from .condition import Condition


class BoolExpression(Condition, Broadcast):
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

    def __await__(self):
        self._start_listening()
        result = (yield from super().__await__())
        self._stop_listening()
        return result

    async def __subscribe__(self, interrupt: CoreInterrupt = None, task: Coroutine = None):
        self._start_listening()
        await super().__subscribe__(interrupt, task)

    async def __trigger__(self):
        await super().__trigger__()
        self._stop_listening()

    async def __on_changed__(self):
        if self._test():
            await self.__trigger__()

    def __repr__(self):
        return '%s %s %s' % (self._left, self._operator_symbol[self._condition], self._right)


V = TypeVar('V')


class Tracked(Generic[V]):
    """
    A value whose changes are tracked to generate events

    The purpose of a tracked value is to derive notification points on the fly.
    Boolean and arithmetic expressions provide events and triggers, respectively:

    .. code:: python

        async def refill(coffee: Tracked[float]):
            while True:
                # boolean expression providing an event to wait for
                await (coffee < 0.5)
                print('Let me refill that for you!')
                # arithmetic expression providing a trigger for waiters
                await (coffee + 0.5)

    :note: A :py:class:`Tracked` object cannot be used in hash-based collections,
           such as keys of a :py:class:`dict` or elements of a :py:class:`set`.
    """
    @property
    def value(self) -> V:
        return self._value

    def __add_listener__(self, listener: BoolExpression):
        self._listeners.append(listener)

    def __del_listener__(self, listener: BoolExpression):
        self._listeners.remove(listener)

    def __init__(self, value: V):
        self._value = value
        self._listeners = []  # type: List[BoolExpression]

    async def set(self, to: V):
        self._value = to
        for listener in self._listeners:
            await listener.__on_changed__()
        await postpone()

    async def __set_expression__(self, to: V):
        await self.set(to)
        return self

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
                        "Use 'await (tracked + 4)' instead")

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


class TrackedExpression:
    """expression to set a tracked value"""
    def __init__(self, value: Tracked[V], to, representation: Callable[[], str] = None):
        self.value = value
        self.to = to
        self._run = False
        self._repr = representation if representation is not None else lambda: '%s.set(%s)' % (value, to)

    def __await__(self):
        if self._run:
            raise RuntimeError("%r cannot be awaited multiple times" % self)
        self._run = True
        yield from self.value.set(self.to).__await__()

    def __repr__(self):
        return self._repr()


if __name__ == "__main__":
    from usim.core import run
    from .notification import until

    async def drink(coffee: Tracked[int]):
        for _ in range(14):
            if coffee >= 5:
                print('*sip*')
                await (coffee - 1)
            else:
                print('only %s sips left :(' % coffee.value)
                await (coffee >= 5)
        print('Enough! Back to work!')
        await (coffee - coffee.value)

    async def refill(coffee: Tracked[int]):
        async with until(coffee <= 0):
            async with until(coffee <= 0):
                while True:
                    await (coffee <= 5)
                    print('Let me refill that for you...')
                    await (coffee + 5)

    cff = Tracked(10)
    run(drink(cff), refill(cff))
