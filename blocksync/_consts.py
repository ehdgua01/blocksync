import re
from pathlib import Path

__all__ = ["BASE_DIR", "ByteSizes", "SAME", "SKIP", "DIFF"]

BASE_DIR = Path(__file__).parent
SAME: str = "0"
SKIP: str = "1"
DIFF: str = "2"


class ByteSizes:
    BLOCK_SIZE_PATTERN = re.compile("([0-9]+)(B|KB|MB|GB|KiB|K|MiB|M|GiB|G)")

    B: int = 1
    KB: int = 1000
    MB: int = 1000 ** 2
    GB: int = 1000 ** 3
    KiB: int = 1 << 10
    K = KiB
    MiB: int = 1 << 20
    M = MiB
    GiB: int = 1 << 30
    G = GiB

    @classmethod
    def parse_readable_byte_size(cls, size: str) -> int:
        """
        Examples
        1MB -> 1000000
        1M, 1MiB -> 10478576
        """
        if not size.isdigit():
            if matched := cls.BLOCK_SIZE_PATTERN.match(size):
                size, unit = matched.group(1), matched.group(2).strip()
                return int(size) * getattr(ByteSizes, unit.upper())
        return int(size)
