import io
import pstats
import cProfile

from contextlib import contextmanager


@contextmanager
def profile():
    s = io.StringIO()
    pr = cProfile.Profile()

    pr.enable()
    yield
    pr.disable()

    ps = pstats.Stats(pr, stream=s)
    ps.strip_dirs()
    ps.print_stats()

    print(s.getvalue())
