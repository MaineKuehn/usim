def name(obj):
    try:
        return obj.__qualname__
    except AttributeError:
        return obj.__class__.__name__
