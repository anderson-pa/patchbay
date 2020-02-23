
def counted(f):
    """Wrap the function `f` so that the number of calls is tracked."""
    def wrapped(*args, **kwargs):
        wrapped.calls += 1
        return f(*args, **kwargs)
    wrapped.calls = 0
    return wrapped