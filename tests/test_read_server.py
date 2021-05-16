import subprocess
from hashlib import sha256

from blocksync._consts import BASE_DIR


def test_read_server(source_file, source_content, pytester):
    p = pytester.popen(
        ["python", (BASE_DIR / "_read_server.py")],
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    stdin, stdout = p.stdin, p.stdout
    stdin.write(f"{source_file}\n".encode())
    assert int(stdout.readline()) == len(source_content)

    stdin.write(f"{len(source_content)}\nsha256\n0\n1\n".encode())
    hashed = sha256(source_content)
    digest = stdout.read(hashed.digest_size)
    assert digest == hashed.digest()

    stdin.write(b"2")
    assert stdout.read(len(source_content)) == source_content
