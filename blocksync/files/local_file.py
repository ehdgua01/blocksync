from __future__ import annotations

import io
from typing import IO

from blocksync.files.interfaces import File

__all__ = ["LocalFile"]


class LocalFile(File):
    def _open(self, mode: str) -> IO:
        return io.open(self.path, mode=mode)
