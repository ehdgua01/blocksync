__all__ = ["ByteSizes", "SSH_PORT"]

SSH_PORT = 22


class ByteSizes:
    KB: int = 1000
    MB: int = 1000 ** 2
    GB: int = 1000 ** 3
    KiB: int = 1 << 10
    MiB: int = 1 << 20
    GiB: int = 1 << 30
