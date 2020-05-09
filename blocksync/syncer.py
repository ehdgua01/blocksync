import os
import logging
import hashlib
import time
from timeit import default_timer as timer
from typing import Set, Dict, Callable

from blocksync.file import File

blocksync_logger = logging.getLogger(__name__)


class Syncer(object):
    def __init__(
        self,
        source: File,
        destination: File,
        workers: int = 1,
        dryrun: bool = False,
        create: bool = False,
        hash_algorithms: Set[str] = None,
        before: Callable = None,
        after: Callable = None,
        monitor: Callable = None,
        on_error: Callable = None,
        interval: int = 5,
        pause: float = 0.5,
    ) -> None:
        if not (isinstance(source, File) and isinstance(destination, File)):
            raise ValueError(
                "Source or(or both) Destination isn't instance of blocksync.File"
            )

        if hash_algorithms and isinstance(hash_algorithms, set):
            if hash_algorithms.difference(hashlib.algorithms_available):
                raise ValueError("Included hash algorithms that are not available")

        self.source = source
        self.destination = destination
        self.workers = workers
        self.dryrun = dryrun
        self.create = create
        self.hash_algorithms = [getattr(hashlib, algo) for algo in hash_algorithms]
        self.blocks: Dict[str, int] = {
            "size": 0,
            "same": 0,
            "diff": 0,
            "done": 0,
            "delta": 0,
            "last": 0,
        }
        self.before = before
        self.after = after
        self.monitor = monitor
        self.on_error = on_error
        self.interval = interval
        self.pause = pause

        self._suspend = False
        self._logger = blocksync_logger

    def __str__(self):
        return "<blocksync.Syncer source={} destination={}>".format(
            self.source, self.destination
        )

    def __repr__(self):
        return "<blocksync.Syncer source={} destination={}>".format(
            self.source, self.destination
        )

    def set_logger(self, logger: logging.Logger) -> "Syncer":
        self._logger = logger
        return self

    def suspend(self) -> "Syncer":
        self._suspend = True
        self._logger.info("Suspending...")
        return self

    def resume(self) -> "Syncer":
        self._suspend = False
        self._logger.info("Resuming...")
        return self

    def _sync(self) -> None:
        try:
            if self.source.do_open().size != self.destination.do_open().size:
                raise ValueError("size not same")

            __block_size = self.source.block_size

            if __block_size != self.destination.block_size:
                self.destination.block_size = __block_size

            self._logger.info("Start sync {}".format(self.destination))

            if self.before:
                self.before(self.blocks)

            t_last = timer()

            for block in zip(self.source.get_blocks(), self.destination.get_blocks()):
                while self._suspend:
                    time.sleep(3)
                    self._logger.info("Suspending...")

                if block[0] == block[1]:
                    self.blocks["same"] += 1
                else:
                    self.blocks["diff"] += 1
                    if not self.dryrun:
                        self.destination.seek(-__block_size, os.SEEK_CUR).write(
                            block[0]
                        )

                self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]

                if self.interval <= t_last - timer():
                    self.blocks["delta"] = self.blocks["done"] - self.blocks["last"]
                    self.blocks["last"] = self.blocks["done"]

                    if self.monitor:
                        self.monitor(self.blocks)

                    t_last = timer()

                if self.blocks["size"] <= (self.blocks["same"] + self.blocks["diff"]):
                    break

                if 0 < self.pause:
                    time.sleep(self.pause)
        finally:
            self.source.do_close()
            self.destination.do_close()

    @property
    def rate(self) -> float:
        return (self.blocks["done"] / self.blocks["size"]) * 100
