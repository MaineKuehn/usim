class NotEmulatedError(NotImplementedError):
    """An operation of the 'simpy' API is not emulated by the 'usim.py' API"""


class StopSimulation(BaseException):
    """Signal to stop a simulation"""


class StopProcess(BaseException):
    """
    Signal to stop a process

    .. warning::

        This exceptions exists for historical compatibility only.
        See :py:meth:`usim.py.Environment.exit` for details.
    """
    def __init__(self, value):
        super().__init__(value)
        self.value = value


class Interrupt(BaseException):
    """Exception used to :py:meth:`~usim.py.events.Process.interrupt` a process"""
    @property
    def cause(self):
        """The ``cause`` passed to :py:meth:`~usim.py.events.Process.interrupt`"""
        return self.args[0]
