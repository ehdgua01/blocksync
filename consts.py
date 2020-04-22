import os
from typing import Dict
from enum import Enum


UNITS: Dict[str, int] = {
    "MiB": 1024 * 1024,
}


class FADV(Enum):
    no_reuse = os.POSIX_FADV_NOREUSE
    dont_need = os.POSIX_FADV_DONTNEED
