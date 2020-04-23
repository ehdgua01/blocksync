from typing import Callable, List

from blocksync.syncer import Syncer
from blocksync.consts import UNITS


class RemoteSyncer(Syncer):
    def sync(
        self,
        src_dev: str,
        dest_dev: List[str],
        block_size: int = UNITS["MiB"],
        interval: int = 1,
        before: Callable = None,
        monitor: Callable = None,
        after: Callable = None,
        on_error: Callable = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Synchronize remote destination file using local source file
        """
        pass
