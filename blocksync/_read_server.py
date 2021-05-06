import base64
import hashlib
import io
import sys
from typing import Callable

DIFF = b"2"
COMPLEN = len(DIFF)
path: bytes = sys.stdin.buffer.readline().strip()

fileobj = open(path, "rb")
fileobj.seek(io.SEEK_SET, io.SEEK_END)
print(fileobj.tell(), flush=True)

block_size: int = int(sys.stdin.buffer.readline())
hash_: Callable = getattr(hashlib, sys.stdin.buffer.readline().strip().decode())
startpos: int = int(sys.stdin.buffer.readline())
maxblock: int = int(sys.stdin.buffer.readline())

with fileobj:
    fileobj.seek(startpos)
    for _ in range(maxblock):
        block = fileobj.read(block_size)
        print(hash_(block).hexdigest(), end="", flush=True)
        if sys.stdin.buffer.read(COMPLEN) == DIFF:
            print(base64.b85encode(block).decode(), end="", flush=True)
