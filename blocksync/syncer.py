from __future__ import annotations

import logging
import logging.handlers
import os
import threading
from typing import List, Tuple, Union

from blocksync.consts import ByteSizes
from blocksync.events import Events
from blocksync.files.interfaces import File
from blocksync.hooks import Hooks
from blocksync.status import Status

__all__ = ["Syncer"]

from blocksync.worker import Worker

blocksync_logger = logging.getLogger(__name__)
blocksync_logger.setLevel(logging.INFO)
blocksync_logger.addHandler(logging.StreamHandler())


class Syncer:
    def __init__(self, source: File, destination: File) -> None:
        self.source = source
        self.destination = destination

        self.status = Status()
        self.events = Events()
        self.hooks = Hooks()

        self.logger: logging.Logger = blocksync_logger

        self._started = False
        self._workers: List[threading.Thread] = []

    def __repr__(self):
        return f"<blocksync.Syncer source={self.source} destination={self.destination}>"

    def start_sync(
        self,
        workers: int = 1,
        block_size: int = ByteSizes.MiB,
        wait: bool = False,
        dryrun: bool = False,
        create: bool = False,
        sync_interval: Union[float, int] = 0.1,
        monitoring_interval: Union[float, int] = 1,
    ) -> Syncer:
        if workers < 1:
            raise ValueError("Workers must be bigger than 1")
        self.status.initialize(block_size=block_size)
        self.events.initialize()
        self._workers = []
        for i in range(1, workers + 1):
            startpos, endpos = self._get_positions(workers, i)
            worker = Worker(
                worker_id=i,
                syncer=self,
                create=create,
                src=self.source,
                dest=self.destination,
                block_size=block_size,
                startpos=startpos,
                endpos=endpos,
                dryrun=dryrun,
                sync_interval=sync_interval,
                monitoring_interval=monitoring_interval,
                logger=self.logger,
            )
            worker.start()
            self._workers.append(worker)
        self._started = True
        if wait:
            self.wait()
        return self

    def _get_positions(self, workers: int, worker_id: int) -> Tuple[int, int]:
        chunk_size = self.source.size // workers
        start = os.SEEK_SET
        end = chunk_size * worker_id
        if 1 < worker_id:
            start = chunk_size * (worker_id - 1)
        if worker_id == workers:
            end += self.source.size % workers
        return start, end

    def wait(self) -> Syncer:
        for worker in self._workers:
            if worker.is_alive():
                worker.join()
        return self

    def suspend(self) -> Syncer:
        self.events.suspended.clear()
        return self

    def resume(self) -> Syncer:
        self.events.suspended.set()
        return self

    @property
    def started(self) -> bool:
        return self._started

    @property
    def finished(self) -> bool:
        if not self._started:
            return False
        for worker in self._workers:
            if worker.is_alive():
                return False
        return True

    @property
    def workers(self) -> List[threading.Thread]:
        return self._workers
