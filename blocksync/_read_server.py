import hashlib
import io
import sys
from typing import Callable

DIFF = b"2"
COMPLEN = len(DIFF)
path: bytes = sys.stdin.buffer.readline().strip()
stdout = sys.stdout.buffer
stdin = sys.stdin.buffer

fileobj = open(path, "rb")
fileobj.seek(io.SEEK_SET, io.SEEK_END)
print(fileobj.tell(), flush=True)

block_size: int = int(stdin.readline())
hash_: Callable = getattr(hashlib, stdin.readline().strip().decode())
startpos: int = int(stdin.readline())
maxblock: int = int(stdin.readline())

with fileobj:
    fileobj.seek(startpos)
    for _ in range(maxblock):
        block = fileobj.read(block_size)
        stdout.write(hash_(block).digest())
        stdout.flush()
        if stdin.read(COMPLEN) == DIFF:
            stdout.write(block)
            stdout.flush()
