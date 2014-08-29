from contextlib import contextmanager

@contextmanager
def open_w_err(filename, mode="r"):
    '''Context manager for opening a file gracefully. See PEP 343, example #6.'''
    try:
        f = open(filename, mode)
    except IOError, err:
        yield None, err
    else:
        try:
            yield f, None
        finally:
            f.close()