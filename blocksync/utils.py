from inspect import signature
from typing import Callable

__all__ = ["validate_callback"]


def validate_callback(c: Callable, n: int = 0):
    if callable(c):
        sig = signature(c)

        if len(sig.parameters) < n:
            raise TypeError(
                "{} required {} arguments, but {}".format(c, n, len(sig.parameters))
            )
        return c
    raise TypeError("{} is not callable".format(c))
