import hashlib
from typing import Set, Dict

from blocksync.file import File


class Task(object):
    def __init__(
        self,
        source: File,
        destination: File,
        workers: int = 1,
        dryrun: bool = False,
        create: bool = False,
        hash_algorithms: Set[str] = None,
    ) -> None:
        if not (isinstance(source, File) and isinstance(destination, File)):
            raise ValueError(
                "Source or(or both) Destination isn't instance of blocksync.File"
            )

        if hash_algorithms and isinstance(hash_algorithms, set):
            if hash_algorithms.difference(hashlib.algorithms_available):
                raise ValueError("Included hash algorithms that are not available")

        self.source = source
        self.destination = destination
        self.workers = workers
        self.dryrun = dryrun
        self.create = create
        self.hash_algorithms = [getattr(hashlib, algo) for algo in hash_algorithms]
        self.blocks: Dict[str, int] = {
            "size": 0,
            "same": 0,
            "diff": 0,
            "chunk_size": 0,
            "start_pos": 0,
            "done": 0,
            "delta": 0,
            "last": 0,
        }

    def get_rate(self) -> float:
        return (self.blocks["done"] / self.blocks["size"]) * 100
