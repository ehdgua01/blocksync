import os
import abc
import logging
from typing import IO, Any, Tuple, Callable, List

from blocksync.consts import FADV, UNITS
from blocksync.exception import StopSync, ForceStopSync

logger = logging.getLogger(__name__)


class Syncer(abc.ABC):
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
        self.logger = logger

    def fadvise(self, fd: IO, offset: int, length: int, advice: FADV) -> None:
        """
        POSIX fadvice

        POSIX_FADV_NOREUSE
        - tells the kernel that the file can be removed from cache,
          flag that gets invalidated if another process is accessing the same file

        POSIX_FADV_DONTNEED
        - removes the file from cache, whether the user is using the file or not
        """
        os.posix_fadvise(fd.fileno(), offset, length, advice.value)

    def do_create(self, path: str, size: int) -> None:
        """
        create file on local

        :param path: file path
        :param size: file size
        """
        with open(path, "a", os.SEEK_SET) as f:
            f.truncate(size)

    def do_open(self, path_: str, mode: str, remote=False) -> Tuple[IO, int]:
        """
        open local file

        :param path_: file path
        :param mode: file open mode
        :param remote: flag of remote file open
        :return: file-object, file size
        """
        if remote:
            if __sftp_client := getattr(self, "_sftp_client", False):
                f = __sftp_client.file(filename=path_, mode=mode)
            else:
                raise Exception("can't get sftp client")
        else:
            f = open(path_, mode)
        f.seek(os.SEEK_SET, os.SEEK_END)
        size = f.tell()
        f.seek(os.SEEK_SET)
        return f, size

    def get_blocks(self, f: IO, block_size: int) -> Any:
        """
        read a block sequentially from the file

        :param f:
        :param block_size:
        :return:
        """
        while block := f.read(block_size):
            yield block

    def get_rate(self) -> float:
        """
        :return: current sync rate
        """
        return (self.blocks["done"] / self.blocks["size"]) * 100

    def stop(self) -> None:
        raise StopSync()

    def force_stop(self) -> None:
        raise ForceStopSync()

    @abc.abstractmethod
    def sync(
        self,
        src_dev: str,
        dest_dev: List[str],
        block_size: int = UNITS["MiB"],
        interval: int = 1,
        before: Callable = None,
        monitor: Callable = None,
        after: Callable = None,
        on_error: Callable = None,
        *args,
        **kwargs,
    ) -> None:
        """Synchronize destination files to source files"""
        pass
