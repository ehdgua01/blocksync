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
        self.source_size: int = 0
        self.destination_size: int = 0
        self.blocks: Blocks = Blocks(same=0, diff=0, done=0)

    def initialize(self, /, block_size: int = ByteSizes.MiB, source_size: int = 0, destination_size: int = 0):
        self.block_size = block_size
        self.source_size = source_size
        self.destination_size = destination_size
        self.blocks = Blocks(same=0, diff=0, done=0)

    def add_block(self, block_type: Literal["same", "diff"]):
        with self._lock:
            self.blocks[block_type] += 1
            self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]

    def get_rate(self) -> float:
        return (
            min(100.00, (self.blocks["done"] / (self.source_size // self.block_size)) * 100)
            if self.blocks["done"] > 1
            else 0.00
        )
