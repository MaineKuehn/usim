class CompatibilityError(BaseException):
    ...


class StopSimulation(BaseException):
    ...


class Interrupt(BaseException):
    @property
    def cause(self):
        return self.args[0]
