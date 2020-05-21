import os
import logging
import hashlib
import time
import threading
import inspect
from timeit import default_timer as timer
from typing import List, Dict, Callable, Any, Union

from blocksync.file import File
from blocksync.utils import validate_callback
from blocksync.interrupt import CancelSync

__all__ = ["Syncer"]

blocksync_logger = logging.getLogger(__name__)


class Syncer(object):
    def __init__(self) -> None:
        self._source = None
        self._destination = None
        self._hash_algorithms: List[Callable] = []

        # callbacks
        self._before = None
        self._after = None
        self._monitor = None
        self._on_error = None

        # internal attributes or properties
        self._lock = threading.Lock()
        self._blocks: Dict[str, int] = {
            "size": -1,
            "same": 0,
            "diff": 0,
            "done": 0,
        }
        self._worker_threads: List[threading.Thread] = []
        self._suspend = False
        self._cancel = False
        self._started = False
        self._logger = blocksync_logger

    def __repr__(self) -> str:
        return "<blocksync.Syncer source={} destination={}>".format(
            self.source, self.destination
        )

    def set_source(self, source: File) -> "Syncer":
        if not isinstance(source, File):
            raise TypeError("Source isn't instance of blocksync.File")
        self._source = source
        return self

    def set_destination(self, destination: File) -> "Syncer":
        if not isinstance(destination, File):
            raise TypeError("Destination isn't instance of blocksync.File")
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
        if isinstance(hash_algorithms, list) and 0 < len(hash_algorithms):
            if set(hash_algorithms).difference(hashlib.algorithms_available):
                raise ValueError("Included hash algorithms that are not available")

            self._hash_algorithms = [getattr(hashlib, algo) for algo in hash_algorithms]
        return self

    def set_logger(self, logger: logging.Logger) -> "Syncer":
        if inspect.isclass(logger):
            logger = logger(__name__)

        if not isinstance(logger, logging.Logger):
            raise TypeError("Logger isn't instance of logging.Logger")

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

    def wait(self) -> "Syncer":
        if self._started and 0 < len(self._worker_threads):
            self._run_alive_workers()
        return self

    def start_sync(
        self,
        workers: int = 1,
        wait: bool = True,
        dryrun: bool = False,
        create: bool = False,
        interval: Union[float, int] = 5,
        pause: Union[float, int] = 0.5,
    ) -> "Syncer":
        if not self.source:
            raise AttributeError("Source is not assigned.")
        elif not self.destination:
            raise AttributeError("Destination is not assigned.")

        if not (isinstance(interval, (float, int)) and isinstance(pause, (float, int))):
            raise TypeError("Interval and pause requires float or int type")

        self._worker_threads = [
            threading.Thread(
                target=self._sync, args=(i, workers, dryrun, create, interval, pause)
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
                data = hash_(data)
        return data

    def _run_alive_workers(self) -> "Syncer":
        for worker in self._alive_workers:
            worker.join()
        return self

    def _sync(
        self,
        worker_id: int,
        workers: int,
        dryrun: bool = False,
        create: bool = False,
        interval: Union[float, int] = 5,
        pause: Union[float, int] = 0.5,
    ) -> None:
        try:
            try:
                self.source.do_open()
                self.destination.do_open()
            except FileNotFoundError:
                if create:
                    self.destination.do_create(self.source.do_open().size).do_open()
                else:
                    raise FileNotFoundError

            if self.source.size != self.destination.size:
                raise ValueError("size not same")
            elif self._blocks["size"] == -1:
                self._blocks["size"] = self.source.size

            chunk_size = self.source.size // workers
            end_pos = chunk_size * worker_id

            if 1 < worker_id:
                start_pos = (chunk_size * (worker_id - 1)) + 1
                self.source.execute("seek", start_pos, os.SEEK_SET)
                self.destination.execute("seek", start_pos, os.SEEK_SET)

                if worker_id == workers:
                    end_pos += self.source.size % workers

            if self.source.block_size != self.destination.block_size:
                self.destination.block_size = self.source.block_size

            self._logger.info("Start sync {}".format(self.destination))

            if self.before:
                self.before(self._blocks)

            t_last = timer()

            try:
                for block in zip(
                    self.source.get_blocks(), self.destination.get_blocks()
                ):
                    while self._suspend:
                        time.sleep(pause)
                        self._logger.info(
                            "[Worker {}]: Suspending...".format(worker_id)
                        )

                    if self._cancel:
                        raise CancelSync(
                            "[Worker {}]: synchronization task has been canceled".format(
                                worker_id
                            )
                        )

                    if block[0] == block[1]:
                        self._add_block("same")
                    else:
                        self._add_block("diff")

                        if not dryrun:
                            self.destination.execute(
                                "seek", -self.source.block_size, os.SEEK_CUR
                            ).execute("write", self._hash(block[0])).execute("flush")

                    if interval <= t_last - timer():
                        if self.monitor:
                            self.monitor(self._blocks)

                        t_last = timer()

                    if end_pos <= self.source.execute_with_result("tell"):
                        self._logger.info(
                            "[Worker {}]: synchronization task has been done".format(
                                worker_id
                            )
                        )
                        break

                    if 0 < pause:
                        time.sleep(pause)

                if self.after:
                    self.after(self._blocks)
            except CancelSync as e:
                self._logger.info(e)
            except Exception as e:
                if self.on_error:
                    self.on_error(e, self._blocks)
        finally:
            self.source.do_close()
            self.destination.do_close()

    @property
    def source(self) -> File:
        return self._source

    @property
    def destination(self) -> File:
        return self._destination

    @property
    def rate(self) -> float:
        return (self._blocks["done"] / self._blocks["size"]) * 100

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
