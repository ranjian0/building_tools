import cProfile
import io
import pstats
import itertools as it
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull


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


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)


def table_print(*iterables, titles=None):
    for items in it.zip_longest(*iterables, fillvalue="None"):
        for i in items:
            print(i, end="\t|\t")
        print()
