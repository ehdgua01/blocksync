from __future__ import annotations

import abc
import os
import threading
from pathlib import Path
from typing import IO, Generator, Optional, Union

import paramiko

from blocksync.consts import ByteSizes

__all__ = ["File"]


class LocalThreadVars(threading.local):
    io: Optional[Union[IO, paramiko.SFTPFile]] = None


class File(abc.ABC):
    _local: LocalThreadVars = LocalThreadVars()

    def __init__(self, path: Union[Path, str]):
        self.path = path
        self.size: int = 0

    def __repr__(self):
        return f"<{self.__class__.__name__} path={self.path} opened={self.opened}>"

    @abc.abstractmethod
    def do_close(self, flush: bool = True) -> File:
        pass

    def do_create(self, size: int) -> File:
        with self._open(mode="w") as f:
            f.truncate(size)
        return self

    def do_open(self) -> File:
        if self.opened:
            return self
        io = self._open(mode="rb+")
        io.seek(os.SEEK_SET, os.SEEK_END)
        self.size = io.tell()
        io.seek(os.SEEK_SET)
        self._local.io = io
        return self

    def get_blocks(self, block_size: int = ByteSizes.MiB) -> Generator[bytes, None, None]:
        while self.opened and (block := self.get_block(block_size)):
            yield block

    def get_block(self, block_size: int = ByteSizes.MiB) -> Optional[bytes]:
        if not (self.opened and self.io):
            return None
        return self.io.read(block_size)

    @abc.abstractmethod
    def _open(self, mode: str) -> Union[IO, paramiko.SFTPFile]:
        pass

    @property
    def io(self) -> Optional[Union[IO, paramiko.SFTPFile]]:
        return self._local.io

    @property
    def opened(self) -> Optional[bool]:
        return not self.io.closed if self.io else False
