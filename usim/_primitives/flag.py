from .condition import Condition
from .notification import postpone


class Flag(Condition):
    """Explicitly settable condition"""
    __slots__ = ('_value', '_inverse')

    def __init__(self):
        super().__init__()
        self._value = False
        self._inverse = InverseFlag(self)

    def __bool__(self) -> bool:
        return self._value

    def __invert__(self) -> 'InverseFlag':
        return self._inverse

    async def set(self, to: bool = True):
        """Set the boolean value of this condition"""
        if to and not self:
            self._value = to
            self.__trigger__()
        elif self and not to:
            self._value = to
            self._inverse.__trigger__()
        await postpone()


class InverseFlag(Condition):
    __slots__ = ('_event',)

    def __init__(self, flag: Flag):
        super().__init__()
        self._event = flag

    def __bool__(self) -> bool:
        return not self._event

    def __invert__(self) -> 'Flag':
        return self._event

    async def set(self, to: bool = True):
        """Set the boolean value of this condition"""
        await self._event.set(not to)
