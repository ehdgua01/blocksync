import io
import sys

DIFF = b"2"
COMPLEN = len(DIFF)
stdin = sys.stdin.buffer

path = stdin.readline().strip()

size = int(stdin.readline())
if size > 0:
    with open(path, "a+") as fileobj:
        fileobj.truncate(size)

block_size = int(stdin.readline())
startpos = int(stdin.readline())
maxblock = int(stdin.readline())

with open(path, mode="rb+") as f:
    f.seek(startpos)
    for _ in range(maxblock):
        if stdin.read(COMPLEN) == DIFF:
            f.write(stdin.read(block_size))
        else:
            f.seek(block_size, io.SEEK_CUR)
