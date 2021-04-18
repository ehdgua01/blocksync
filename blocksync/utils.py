import random
import string

__all__ = ["generate_random_data"]


def generate_random_data(size: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=size))
