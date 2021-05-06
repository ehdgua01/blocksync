import threading
from typing import List


class SyncManager:
    def __init__(self):
        self.workers: List[threading.Thread] = []
        self._suspend: threading.Event = threading.Event()
        self._suspend.set()
        self._cancel: bool = False

    def cancel_sync(self):
        self._cancel = True

    def wait_sync(self):
        for worker in self.workers:
            worker.join()

    def suspend(self):
        self._suspend.clear()

    def resume(self):
        self._suspend.set()

    def _wait_resuming(self):
        self._suspend.wait()

    @property
    def canceled(self) -> bool:
        return self._cancel

    @property
    def suspended(self) -> bool:
        return not self._suspend.is_set()

    @property
    def finished(self) -> bool:
        for worker in self.workers:
            if worker.is_alive():
                return False
        return True
