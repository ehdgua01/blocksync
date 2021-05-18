import threading
from typing import Literal, TypedDict


class Blocks(TypedDict):
    same: int
    diff: int
    done: int


class Status:
    def __init__(
        self,
        workers: int,
        block_size: int,
        src_size: int,
        dest_size: int = 0,
    ):
        self._lock = threading.Lock()
        self.workers: int = workers
        self.chunk_size: int = src_size // workers
        self.block_size: int = block_size
        self.src_size: int = src_size
        self.dest_size: int = dest_size
        self.blocks: Blocks = Blocks(same=0, diff=0, done=0)

    def __repr__(self):
        return str({k: v for k, v in self.__dict__.items() if k != "_lock"})

    def add_block(self, block_type: Literal["same", "diff"]):
        with self._lock:
            self.blocks[block_type] += 1
            self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]

    @property
    def rate(self) -> float:
        return (
            min(100.00, (self.blocks["done"] / (self.src_size // self.block_size)) * 100)
            if self.blocks["done"] > 1
            else 0.00
        )
