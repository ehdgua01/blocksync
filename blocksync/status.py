import threading
from typing import Literal, TypedDict

from blocksync.consts import ByteSizes


class Blocks(TypedDict):
    same: int
    diff: int
    done: int


class Status:
    def __init__(self):
        self._lock = threading.Lock()
        self.block_size: int = ByteSizes.MiB
        self._source_size: int = 0
        self._destination_size: int = 0
        self._blocks: Blocks = Blocks(same=0, diff=0, done=0)

    def initialize(self, /, block_size: int = ByteSizes.MiB, source_size: int = 0, destination_size: int = 0):
        self.block_size = block_size
        self._source_size = source_size
        self._destination_size = destination_size
        self._blocks = Blocks(same=0, diff=0, done=0)

    def _add_block(self, block_type: Literal["same", "diff"]):
        with self._lock:
            self._blocks[block_type] += 1
            self._blocks["done"] = self._blocks["same"] + self._blocks["diff"]

    @property
    def source_size(self) -> int:
        return self._source_size

    @property
    def destination_size(self) -> int:
        return self._destination_size

    @property
    def blocks(self) -> Blocks:
        return self._blocks

    @property
    def rate(self) -> float:
        return (
            min(100.00, (self._blocks["done"] / (self._source_size // self.block_size)) * 100)
            if self._blocks["done"] > 1
            else 0.00
        )
