from __future__ import annotations

import io
from typing import IO

from blocksync.files.interfaces import File

__all__ = ["LocalFile"]


class LocalFile(File):
    def do_close(self, flush=True) -> File:
        if self.opened:
            if flush:
                self.io.flush()  # type: ignore[union-attr]
            self.io.close()  # type: ignore[union-attr]
        return self

    def _open(self, mode: str) -> IO:
        return io.open(self.path, mode=mode)
