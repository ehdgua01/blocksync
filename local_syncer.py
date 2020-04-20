from typing import Callable

from .syncer import Syncer


class LocalSyncer(Syncer):
    def sync(
        self,
        src_dev: str,
        dest_dev: str,
        before: Callable = None,
        monitor: Callable = None,
        after: Callable = None,
        on_error: Callable = None,
    ):
        pass
