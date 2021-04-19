from typing import Callable, Optional

from blocksync.status import Status

__all__ = ["Hooks"]


class Hooks:
    def __init__(self):
        self.root_before: Optional[Callable] = None
        self.before: Optional[Callable] = None
        self.root_after: Optional[Callable] = None
        self.after: Optional[Callable] = None
        self.monitor: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def _run(self, hook: Optional[Callable], *args, **kwargs):
        if hook:
            hook(*args, **kwargs)

    def run_root_before(self):
        self._run(self.root_before)

    def run_before(self):
        self._run(self.before)

    def run_root_after(self, status: Status):
        self._run(self.root_after, status)

    def run_after(self, status: Status):
        self._run(self.after, status)

    def run_monitor(self, status: Status):
        self._run(self.monitor, status)

    def run_on_error(self, exc: Exception, status: Status):
        self._run(self.on_error, exc, status)
