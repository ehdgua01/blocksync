import threading
from typing import Literal, TypedDict

BlockTypes = Literal["same", "diff", "done"]


class Blocks(TypedDict):
    same: int
    diff: int
    done: int


class Status(threading.Lock):
    def __init__(self):
        super(Status, self).__init__()
        self.block_size: int = 0
        self.source_size: int = 0
        self.destination_size: int = 0
        self.blocks: Blocks = Blocks(same=0, diff=0, done=0)

    def initialize(self, /, block_size: int = 0, source_size: int = 0, destination_size: int = 0):
        self.block_size = block_size
        self.source_size = source_size
        self.destination_size = destination_size
        self.blocks = Blocks(same=0, diff=0, done=0)

    def add_block(self, block_type: BlockTypes):
        if block_type == "done":
            raise ValueError("DONE blocks are automatically calculated.")
        with self:
            self.blocks[block_type] += 1
            self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]

    def get_rate(self, block_size: int) -> float:
        return (
            min(100.00, (self.blocks["done"] / (self.source_size // block_size)) * 100)
            if self.blocks["done"] > 1
            else 0.00
        )
