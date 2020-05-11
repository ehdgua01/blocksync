from typing import Dict

__all__ = ["UNITS", "SSH_PORT"]


UNITS: Dict[str, int] = {
    "KB": 1000,
    "MB": 1000 ** 2,
    "GB": 1000 ** 3,
    "KiB": 1 << 10,
    "MiB": 1 << 20,
    "GiB": 1 << 30,
}
SSH_PORT = 22
