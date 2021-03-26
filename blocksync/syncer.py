import hashlib
import logging
import os
import threading
import time
from timeit import default_timer as timer
from typing import Any, Callable, Dict, List, Optional, Union

from blocksync.consts import UNITS
from blocksync.file import File
from blocksync.interrupt import CancelSync
from blocksync.utils import validate_callback

__all__ = ["Syncer"]

blocksync_logger = logging.getLogger(__name__)


class Syncer(object):
    def __init__(self, source: File, destination: File) -> None:
        self._source = source
        self._destination = destination
        self._hash_algorithms: List[Callable] = []

        # callbacks
        self._before: Optional[Callable] = None
        self._after: Optional[Callable] = None
        self._monitor: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # internal attributes or properties
        self._lock = threading.Lock()
        self._create = threading.Event()
        self._suspend = threading.Event()
        self._blocks: Dict[str, int] = {
            "size": -1,
            "same": 0,
            "diff": 0,
            "done": 0,
        }
        self._worker_threads: List[threading.Thread] = []
        self._cancel = False
        self._started = False
        self._logger = blocksync_logger

    def __repr__(self):
        return "<blocksync.Syncer source={} destination={}>".format(self.source, self.destination)

    def set_source(self, source: File) -> "Syncer":
        self._source = source
        return self

    def set_destination(self, destination: File) -> "Syncer":
        self._destination = destination
        return self

    def set_callbacks(
        self,
        before: Callable = None,
        after: Callable = None,
        monitor: Callable = None,
        on_error: Callable = None,
    ) -> "Syncer":
        if before and validate_callback(before, 1):
            self._before = before

        if after and validate_callback(after, 1):
            self._after = after

        if monitor and validate_callback(monitor, 1):
            self._monitor = monitor

        if on_error and validate_callback(on_error, 2):
            self._on_error = on_error
        return self

    def set_hash_algorithms(self, hash_algorithms: List[str]) -> "Syncer":
        if set(hash_algorithms).difference(hashlib.algorithms_available):
            raise ValueError("Included hash algorithms that are not available")
        self._hash_algorithms = [getattr(hashlib, algo) for algo in hash_algorithms]
        return self

    def set_logger(self, logger: logging.Logger) -> "Syncer":
        if not isinstance(logger, logging.Logger):
            raise TypeError("Logger isn't instance of logging.Logger")
        self._logger = logger
        return self

    def suspend(self) -> "Syncer":
        self._suspend.clear()
        self._logger.info("Suspending...")
        return self

    def resume(self) -> "Syncer":
        self._suspend.set()
        self._logger.info("Resuming...")
        return self

    def cancel(self) -> "Syncer":
        self._cancel = True
        self._logger.info("Canceling...")
        return self

    def wait(self) -> "Syncer":
        if self._started and 0 < len(self._worker_threads):
            self._run_alive_workers()
        return self

    def reset_blocks(self) -> "Syncer":
        self._blocks.update({"size": -1, "same": 0, "diff": 0, "done": 0})
        return self

    def start_sync(
        self,
        workers: int = 1,
        block_size: int = UNITS["MiB"],
        wait: bool = False,
        dryrun: bool = False,
        create: bool = False,
        interval: Union[float, int] = 1,
        pause: Union[float, int] = 0.1,
    ) -> "Syncer":
        self.reset_blocks()
        self._create.clear()
        self._suspend.set()
        self._worker_threads = [
            threading.Thread(
                target=self._sync,
                args=(i, workers, block_size, dryrun, create, interval, pause),
            )
            for i in range(1, workers + 1)
        ]

        for worker in self._worker_threads:
            worker.start()

        self._started = True

        if wait:
            self._run_alive_workers()
        return self

    def _add_block(self, block: str) -> None:
        with self._lock:
            if block in self._blocks:
                self._blocks[block] += 1
                self._blocks["done"] = self._blocks["same"] + self._blocks["diff"]

    def _hash(self, data: Any) -> Any:
        if 0 < len(self._hash_algorithms):
            for hash_ in self._hash_algorithms:
                data = hash_(data).digest()
        return data

    def _run_alive_workers(self) -> "Syncer":
        for worker in self._alive_workers:
            worker.join()
        return self

    def _sync(
        self,
        worker_id: int,
        workers: int,
        block_size: int,
        dryrun: bool = False,
        create: bool = False,
        interval: Union[float, int] = 1,
        pause: Union[float, int] = 0.1,
    ) -> None:
        try:
            self.source.do_open()
            try:
                self.destination.do_open()
            except FileNotFoundError:
                if create:
                    if worker_id == 1:
                        self.destination.do_create(self.source.size)
                        self._create.set()
                    else:
                        self._create.wait()
                    self.destination.do_close().do_open()
                else:
                    raise

            if self.source.size != self.destination.size:
                self._logger.error("size not same")
                return
            elif self._blocks["size"] == -1:
                self._blocks["size"] = self.source.size

            chunk_size = self.source.size // workers
            end_pos = chunk_size * worker_id

            if 1 < worker_id:
                start_pos = chunk_size * (worker_id - 1)
                self.source.execute("seek", start_pos, os.SEEK_SET)
                self.destination.execute("seek", start_pos, os.SEEK_SET)

                if worker_id == workers:
                    end_pos += self.source.size % workers

            self._logger.info("Start sync {}".format(self.destination))

            if self.before:
                self.before(self._blocks)

            t_last = timer()

            try:
                for source_block, dest_block in zip(
                    self.source.get_blocks(block_size),
                    self.destination.get_blocks(block_size),
                ):
                    if not self._suspend.is_set():
                        self._logger.info("[Worker {}]: Suspending...".format(worker_id))
                        self._suspend.wait()

                    if self._cancel:
                        raise CancelSync("[Worker {}]: synchronization task has been canceled".format(worker_id))

                    if self._hash(source_block) == self._hash(dest_block):
                        self._add_block("same")
                    else:
                        self._add_block("diff")

                        if not dryrun:
                            offset = min(len(source_block), block_size)
                            self.destination.execute("seek", -offset, os.SEEK_CUR).execute(
                                "write", source_block
                            ).execute("flush")

                    if interval <= timer() - t_last:
                        if self.monitor:
                            self.monitor(self._blocks)

                        t_last = timer()

                    if end_pos <= self.source.execute_with_result("tell"):
                        self._logger.info("[Worker {}]: synchronization task has been done".format(worker_id))
                        break

                    if 0 < pause:
                        time.sleep(pause)

                if self.after:
                    self.after(self._blocks)
            except CancelSync as e:
                self._logger.info(e)
            except Exception as e:
                if self.on_error:
                    return self.on_error(e, self._blocks)
        finally:
            self.source.do_close()
            self.destination.do_close()

    def get_rate(self, block_size: int = UNITS["MiB"]) -> float:
        if self._blocks["done"] < 1:
            return 0.00

        rate = (self._blocks["done"] / (self._blocks["size"] // block_size or 1)) * 100
        return 100.00 if 100 <= rate else rate

    @property
    def source(self) -> File:
        return self._source

    @property
    def destination(self) -> File:
        return self._destination

    @property
    def blocks(self) -> Dict[str, int]:
        return self._blocks

    @property
    def hash_algorithms(self) -> List[Callable]:
        return self._hash_algorithms

    @property
    def started(self) -> bool:
        return self._started

    @property
    def finished(self) -> bool:
        if self._started and len(self._alive_workers) < 1:
            return True
        return False

    @property
    def before(self) -> Union[Callable, None]:
        return self._before

    @property
    def after(self) -> Union[Callable, None]:
        return self._after

    @property
    def monitor(self) -> Union[Callable, None]:
        return self._monitor

    @property
    def on_error(self) -> Union[Callable, None]:
        return self._on_error

    @property
    def _alive_workers(self) -> List[threading.Thread]:
        return [w for w in self._worker_threads if w.is_alive()]
