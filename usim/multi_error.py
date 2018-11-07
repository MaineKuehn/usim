class MultiError(Exception):
    def __init__(self, *children: Exception):
        self.children = children
        super().__init__(self)
        if len(children) == 1 and self.__cause__ is self.__context__ is None:
            self.__cause__ = self.children[0]

    def __str__(self):
        return ', '.join(repr(child) for child in self.children)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self)
