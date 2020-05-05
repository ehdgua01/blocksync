import os
from typing import Dict
from enum import Enum


UNITS: Dict[str, int] = {
    "KB": 1000,
    "MB": 1000 ** 2,
    "GB": 1000 ** 3,
    "KiB": 1 << 10,
    "MiB": 1 << 20,
    "GiB": 1 << 30,
}
SSH_PORT = 22


class FADV(Enum):
    no_reuse = os.POSIX_FADV_NOREUSE
    dont_need = os.POSIX_FADV_DONTNEED
