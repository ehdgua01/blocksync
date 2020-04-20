import os
import abc
from typing import IO, Any, Tuple
from enum import Enum


class FADV(Enum):
    no_reuse = os.POSIX_FADV_NOREUSE
    dont_need = os.POSIX_FADV_DONTNEED


class Syncer(abc.ABC):
    MiB = 1024 * 1024

    def __init__(self) -> None:
        """
        size = source file size
        same = size of between two file same blocks
        diff = size of between two file diff blocks
        done = computed blocks
        delta = number of blocks lately changed
        last = recent block location
        """
        self.blocks = {
            "size": 0,
            "same": 0,
            "diff": 0,
            "done": 0,
            "delta": 0,
            "last": 0,
        }

    def fadvise(self, fd: IO, offset: int, length: int, advice: FADV) -> None:
        """
        POSIX_FADV_NOREUSE
        - tells the kernel that the file can be removed from cache,
          flag that gets invalidated if another process is accessing the same file

        POSIX_FADV_DONTNEED
        - removes the file from cache, whether the user is using the file or not
        """
        os.posix_fadvise(fd.fileno(), offset, length, advice.value)

    def do_create(self, path: str, size: int) -> None:
        """
        :param path: file path
        :param size: file size
        """
        with open(path, "a", os.SEEK_SET) as f:
            f.truncate(size)

    def do_open(self, path_: str, mode: str) -> Tuple[IO, int]:
        """
        :param path_: file path
        :param mode: file open mode
        :return: file-object, file size
        """
        f = open(path_, mode)
        self.fadvise(f, 0, 0, FADV.no_reuse)
        f.seek(os.SEEK_SET, os.SEEK_END)
        size = f.tell()
        f.seek(os.SEEK_SET)
        return f, size

    def get_blocks(self, f: IO, block_size: int) -> Any:
        """

        :param f:
        :param block_size:
        :return:
        """
        while block := f.read(block_size):
            self.fadvise(
                f, f.tell() - block_size, block_size, FADV.dont_need,
            )
            yield block

    def get_rate(self) -> float:
        """
        :return: current sync rate
        """
        return (self.blocks["done_blocks"] / self.blocks["size"]) * 100

    @abc.abstractmethod
    def sync(self, *args, **kwargs) -> Any:
        pass
