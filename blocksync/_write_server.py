import io
import sys

DIFF = b"2"
COMPLEN = len(DIFF)
path = sys.stdin.buffer.readline().strip()
block_size = int(sys.stdin.buffer.readline())
size = int(sys.stdin.buffer.readline())
if size > 0:
    with open(path, "a+") as fileobj:
        fileobj.truncate(size)

startpos = int(sys.stdin.buffer.readline())
maxblock = int(sys.stdin.buffer.readline())

with open(path, mode="rb+") as f:
    f.seek(startpos)
    for _ in range(maxblock):
        if sys.stdin.buffer.read(COMPLEN) == DIFF:
            current_block_size: int = int(sys.stdin.buffer.readline())
            diff = sys.stdin.buffer.read(current_block_size)
            f.write(diff)
        else:
            f.seek(block_size, io.SEEK_CUR)
