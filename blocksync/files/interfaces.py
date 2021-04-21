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
    def __init__(self, path: Union[Path, str]):
        self._local: LocalThreadVars = LocalThreadVars()
        self.path: Union[Path, str] = path
        self.size: int = 0

    def __repr__(self):
        return f"<{self.__class__.__name__} path={self.path} opened={self.opened}>"

    def do_close(self, flush: bool = True) -> File:
        if self.opened:
            if flush:
                self.io.flush()  # type: ignore[union-attr]
            self.io.close()  # type: ignore[union-attr]
        return self

    def do_create(self, size: int) -> File:
        with self._open(mode="w") as f:
            f.truncate(size)
        return self

    def do_open(self) -> File:
        fileobj = self._open(mode="rb+")
        self._local.io = fileobj
        self.size = self._get_size(fileobj)
        return self

    def get_blocks(self, block_size: int = ByteSizes.MiB) -> Generator[bytes, None, None]:
        while self.opened and (block := self.get_block(block_size)):
            yield block

    def get_block(self, block_size: int = ByteSizes.MiB) -> Optional[bytes]:
        return self.io.read(block_size) if self.opened and self.io else None

    @abc.abstractmethod
    def _open(self, mode: str) -> Union[IO, paramiko.SFTPFile]:
        raise NotImplementedError

    def _get_size(self, fileobj: Union[IO, paramiko.SFTPFile]) -> int:
        fileobj.seek(os.SEEK_SET, os.SEEK_END)
        size = fileobj.tell()
        fileobj.seek(os.SEEK_SET)
        return size

    @property
    def io(self) -> Optional[Union[IO, paramiko.SFTPFile]]:
        return self._local.io

    @property
    def opened(self) -> bool:
        if io := self.io:
            return not io.closed
        return False
