from typing import Any, Callable, Optional

from blocksync._status import Status

__all__ = ["Hooks"]


class Hooks:
    def __init__(self):
        self.before: Optional[Callable[[None], Any]] = None
        self.after: Optional[Callable[[Status], Any]] = None
        self.monitor: Optional[Callable[[Status], Any]] = None
        self.on_error: Optional[Callable[[Status], Any]] = None

    def _run(self, hook: Optional[Callable], *args, **kwargs):
        if hook:
            hook(*args, **kwargs)

    def run_before(self):
        self._run(self.before)

    def run_after(self, status: Status):
        self._run(self.after, status)

    def run_monitor(self, status: Status):
        self._run(self.monitor, status)

    def run_on_error(self, exc: Exception, status: Status):
        self._run(self.on_error, exc, status)
