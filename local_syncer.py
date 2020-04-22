import os
import time
import logging
from typing import Callable

from syncer import Syncer
from consts import UNITS

logger = logging.getLogger(__name__)


class LocalSyncer(Syncer):
    def sync(
        self,
        src_dev: str,
        dest_dev: str,
        block_size: int = UNITS["MiB"],
        interval: int = 1,
        before: Callable = None,
        monitor: Callable = None,
        after: Callable = None,
        on_error: Callable = None,
        *args,
        **kwargs,
    ) -> None:
        if src_dev == dest_dev:
            raise ValueError("Error same source and destination")

        if before:
            before(*args, **kwargs)

        src_dev, src_size = self.do_open(src_dev, "rb+")
        dest_dev, dest_size = self.do_open(dest_dev, "rb+")

        try:
            if src_size != dest_size:
                raise ValueError("Error devices size not same")

            try:
                self.blocks["size"] = src_size
                t_last = 0

                for idx, block in enumerate(
                    zip(
                        self.get_blocks(src_dev, block_size),
                        self.get_blocks(dest_dev, block_size),
                    )
                ):
                    if block[0] == block[1]:
                        self.blocks["same"] += 1
                    else:
                        dest_dev.seek(-block_size, os.SEEK_CUR)
                        dest_dev.write(block[0])
                        self.blocks["diff"] += 1

                    self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]
                    self.blocks["delta"] = self.blocks["done"] - self.blocks["last"]
                    self.blocks["last"] = self.blocks["done"]
                    t1 = time.time()

                    if t1 - t_last >= interval:
                        if monitor:
                            monitor(*args, **kwargs)

                        t_last = t1

                    if (self.blocks["same"] + self.blocks["diff"]) == self.blocks[
                        "size"
                    ]:
                        break
                if after:
                    after(*args, **kwargs)
            except Exception as e:
                logger.error(e)
                on_error(*args, **kwargs)
        finally:
            src_dev.close()
            dest_dev.close()
