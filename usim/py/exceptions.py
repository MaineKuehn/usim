class CompatibilityError(BaseException):
    ...


class StopSimulation(BaseException):
    ...


class StopProcess(BaseException):
    def __init__(self, value):
        super().__init__(value)
        self.value = value


class Interrupt(BaseException):
    @property
    def cause(self):
        return self.args[0]
