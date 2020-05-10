import os
import logging
import hashlib
import time
from timeit import default_timer as timer
from typing import Set, Dict, Callable

from blocksync.file import File
from blocksync.utils import validate_callback
from blocksync.interrupt import CancelSync

__all__ = ["Syncer"]

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
        self.before = validate_callback(before, 1)
        self.after = validate_callback(after, 1)
        self.monitor = validate_callback(monitor, 1)
        self.on_error = validate_callback(on_error, 2)
        self.interval = interval
        self.pause = pause

        self._suspend = False
        self._cancel = False
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

    def cancel(self) -> "Syncer":
        self._cancel = True
        self._logger.info("Canceling...")
        return self

    def _sync(self, worker_id: int) -> None:
        try:
            try:
                self.source.do_open()
                self.destination.do_open()
            except FileNotFoundError:
                if self.create:
                    self.destination.do_create(self.source.do_open().size).do_open()

            if self.source.size != self.destination.size:
                raise ValueError("size not same")

            chunk_size = self.source.size // self.workers
            end_pos = chunk_size * worker_id

            if 1 < worker_id:
                start_pos = (chunk_size * (worker_id - 1)) + 1
                self.source.execute("seek", start_pos, os.SEEK_SET)
                self.destination.execute("seek", start_pos, os.SEEK_SET)

                if worker_id == self.workers:
                    end_pos += self.source.size % self.workers

            if self.source.block_size != self.destination.block_size:
                self.destination.block_size = self.source.block_size

            self._logger.info("Start sync {}".format(self.destination))

            if self.before:
                self.before(self.blocks)

            t_last = timer()

            for block in zip(self.source.get_blocks(), self.destination.get_blocks()):
                while self._suspend:
                    time.sleep(self.pause)
                    self._logger.info("[Worker {}]: Suspending...".format(worker_id))

                if self._cancel:
                    raise CancelSync()

                if block[0] == block[1]:
                    self.blocks["same"] += 1
                else:
                    self.blocks["diff"] += 1
                    if not self.dryrun:
                        self.destination.execute(
                            "seek", -self.source.block_size, os.SEEK_CUR
                        ).execute("write", block[0]).execute("flush")

                self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]

                if self.interval <= t_last - timer():
                    self.blocks["delta"] = self.blocks["done"] - self.blocks["last"]
                    self.blocks["last"] = self.blocks["done"]

                    if self.monitor:
                        self.monitor(self.blocks)

                    t_last = timer()

                if end_pos <= self.source.execute_with_result("tell"):
                    self._logger.info(
                        "[Worker {}]: synchronization task has been done".format(
                            worker_id
                        )
                    )
                    break

                if 0 < self.pause:
                    time.sleep(self.pause)

            if self.after:
                self.after(self.blocks)
        except CancelSync:
            self._logger.info(
                "[Worker {}]: synchronization task has been canceled".format(worker_id)
            )
        except Exception as e:
            if self.on_error:
                self.on_error(e, self.blocks)
        finally:
            self.source.do_close()
            self.destination.do_close()

    @property
    def rate(self) -> float:
        return (self.blocks["done"] / self.blocks["size"]) * 100
