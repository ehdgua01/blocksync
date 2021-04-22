from __future__ import annotations

import logging
import os
import threading
import time
from timeit import default_timer as timer
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from blocksync import Syncer

__all__ = ["Worker"]


class Worker(threading.Thread):
    def __init__(
        self,
        worker_id: int,
        syncer: Syncer,
        startpos: int,
        endpos: int,
        dryrun: bool,
        sync_interval: Union[int, float],
        monitoring_interval: Union[int, float],
        logger: logging.Logger,
    ):
        super().__init__()
        self.worker_id = worker_id
        self.syncer: Syncer = syncer
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
            self.syncer.src.do_close()
            self.syncer.dest.do_close()

    def _sync(self):
        self.syncer.src.do_open().io.seek(self.startpos)  # type: ignore[union-attr]
        self.syncer.dest.do_open().io.seek(self.startpos)  # type: ignore[union-attr]

        self._log(
            f"Start sync(startpos: {self.startpos}, endpos: {self.endpos}) {self.syncer.src} to {self.syncer.dest}"
        )
        self.syncer.hooks.run_before()

        t_last = timer()
        try:
            for source_block, dest_block in zip(
                self.syncer.src.get_blocks(self.syncer.status.block_size),
                self.syncer.dest.get_blocks(self.syncer.status.block_size),
            ):
                if self.syncer.suspended:
                    self._log("Suspending...")
                    self.syncer._suspended.wait()
                if self.syncer.canceled:
                    self._log("Synchronization task has been canceled")
                    return
                if source_block == dest_block:
                    self.syncer.status._add_block("same")
                else:
                    self.syncer.status._add_block("diff")
                    if not self.dryrun:
                        offset = min(len(source_block), len(dest_block), self.syncer.status.block_size)
                        self.syncer.dest.io.seek(-offset, os.SEEK_CUR)  # type: ignore[union-attr]
                        self.syncer.dest.io.write(source_block)  # type: ignore[union-attr]
                        self.syncer.dest.io.flush()  # type: ignore[union-attr]
                t_cur = timer()
                if self.monitoring_interval <= t_cur - t_last:
                    self.syncer.hooks.run_monitor(self.syncer.status)
                    t_last = t_cur
                if self.endpos <= self.syncer.src.io.tell():  # type: ignore[union-attr]
                    self._log("!!! Done !!!")
                    break
                if 0 < self.sync_interval:
                    time.sleep(self.sync_interval)
            self.syncer.hooks.run_after(self.syncer.status)
        except Exception as e:
            self._log(str(e), level=logging.ERROR, exc_info=True)
            self.syncer.hooks.run_on_error(e, self.syncer.status)
        return

    def _log(self, msg: str, level: int = logging.INFO, *args, **kwargs):
        self.logger.log(level, f"[Worker {self.worker_id}]: {msg}", *args, **kwargs)
