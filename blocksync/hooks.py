from typing import Callable, Optional

from blocksync.status import Blocks

__all__ = ["Hooks"]


class Hooks:
    def __init__(self):
        self.before: Optional[Callable] = None
        self.after: Optional[Callable] = None
        self.monitor: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def _run(self, hook: Optional[Callable], *args, **kwargs):
        try:
            hook(*args, **kwargs)  # type: ignore[misc]
        except TypeError:
            pass

    def run_before(self, blocks: Blocks):
        self._run(self.before, blocks)

    def run_after(self, blocks: Blocks):
        self._run(self.after, blocks)

    def run_monitor(self, blocks: Blocks):
        self._run(self.monitor, blocks)

    def run_on_error(self, exc: Exception, blocks: Blocks):
        self._run(self.on_error, exc, blocks)
