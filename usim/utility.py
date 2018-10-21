def __repr__(self):
    return '%s(%s)' % (
        self.__class__.__name__,
        ', '.join(
            '%s=%s' % (key, value)
            for key, value in self.__dict__
        )
    )
