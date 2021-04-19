from __future__ import annotations

import logging
import os
import threading
import time
from timeit import default_timer as timer
from typing import TYPE_CHECKING, Union

from blocksync.files import File

if TYPE_CHECKING:
    from blocksync import Syncer

__all__ = ["Worker"]


class Worker(threading.Thread):
    def __init__(
        self,
        worker_id: int,
        syncer: Syncer,
        create: bool,
        src: File,
        dest: File,
        startpos: int,
        endpos: int,
        dryrun: bool,
        sync_interval: Union[int, float],
        monitoring_interval: Union[int, float],
        logger: logging.Logger,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.worker_id = worker_id
        self.syncer: Syncer = syncer
        self.src: File = src
        self.dest: File = dest
        self.startpos: int = startpos
        self.endpos: int = endpos
        self.dryrun: bool = dryrun
        self.sync_interval = sync_interval
        self.monitoring_interval = monitoring_interval
        self.logger: logging.Logger = logger

    def run(self):
        self.syncer.hooks.run_root_before()
        try:
            self._sync()
            self.syncer.hooks.run_root_after(self.syncer.status)
        finally:
            self.src.do_close()
            self.dest.do_close()

    def _sync(self):
        self.src.do_open().io.seek(self.startpos)  # type: ignore[union-attr]
        self.dest.do_open().io.seek(self.startpos)  # type: ignore[union-attr]

        self._log(f"Start sync {self.src} to {self.dest}")
        self.syncer.hooks.run_before()

        t_last = timer()
        try:
            for source_block, dest_block in zip(
                self.src.get_blocks(self.syncer.status.block_size),
                self.dest.get_blocks(self.syncer.status.block_size),
            ):
                if not self.syncer.events.suspended.is_set():
                    self._log("Suspending...")
                    self.syncer.events.suspended.wait()
                if not self.syncer.events.canceled.is_set():
                    self._log("Synchronization task has been canceled")
                    return
                if source_block == dest_block:
                    self.syncer.status._add_block("same")
                else:
                    self.syncer.status._add_block("diff")
                    if not self.dryrun:
                        offset = min(len(source_block), self.syncer.status.block_size)
                        self.dest.io.seek(-offset, os.SEEK_CUR)  # type: ignore[union-attr]
                        self.dest.io.write(source_block)  # type: ignore[union-attr]
                        self.dest.io.flush()  # type: ignore[union-attr]
                if self.monitoring_interval <= timer() - t_last:
                    self.syncer.hooks.run_monitor(self.syncer.status)
                    t_last = timer()
                if self.endpos <= self.src.io.tell():  # type: ignore[union-attr]
                    self._log("!!! Done !!!")
                    break
                if 0 < self.sync_interval:
                    time.sleep(self.sync_interval)
            self.syncer.hooks.run_after(self.syncer.status)
        except Exception as e:
            self._log(str(e), level=logging.ERROR, exc_info=True)
            self.syncer.hooks.run_on_error(e, self.syncer.status)

    def _log(self, msg: str, level=logging.INFO, *args, **kwargs):
        self.logger.log(level, f"[Worker {self.worker_id}]: {msg}", *args, **kwargs)
