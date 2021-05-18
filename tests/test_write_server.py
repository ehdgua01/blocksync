import subprocess

from blocksync._consts import BASE_DIR


def test_write_server(pytester):
    p = pytester.popen(
        ["python", (BASE_DIR / "_write_server.py")],
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    stdin = p.stdin
    dest_file_path = str(pytester.path / "dest.img")
    expected_dest_file_content = b"a" * 20
    stdin.write(f"{dest_file_path}\n20\n20\n0\n1\n".encode())
    stdin.write(b"2")
    stdin.write(expected_dest_file_content)
    p.wait()
    dest_file = open(dest_file_path, "rb")
    assert dest_file.read() == expected_dest_file_content
