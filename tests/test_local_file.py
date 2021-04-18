import os
import unittest.mock
from pathlib import Path

import pytest

from blocksync import LocalFile


@pytest.fixture
def stub_local_file(tmp_path):
    path = tmp_path / "local.file"
    file = LocalFile(path)
    return file.do_create(10)


def get_file_size(path: Path):
    file = open(path, "r")
    file.seek(os.SEEK_SET, os.SEEK_END)
    return file.tell()


def test_do_create(tmp_path):
    # Expect: Create a file of a specific size
    path = tmp_path / "local.file"
    file = LocalFile(path)
    file.do_create(10)
    assert path.exists()
    assert get_file_size(path) == 10


def test_do_open(stub_local_file):
    # When: Create file and open it
    stub_local_file.do_open()

    # Then: File opened for reading and writing in binary mode
    assert stub_local_file.io.mode == "rb+"

    # And: File positioning is file's start
    assert stub_local_file.io.tell() == 0

    # And: Set file.size to actual file size
    assert stub_local_file.size == get_file_size(stub_local_file.path)


def test_do_close(stub_local_file):
    # Expect: File closed
    stub_local_file.do_open().do_close()
    assert stub_local_file.io.closed
    with pytest.raises(ValueError, match="closed file"):
        stub_local_file.io.write(b"test")

    # Expect: Don't flush
    io = stub_local_file.io
    io.flush = unittest.mock.Mock()
    stub_local_file.do_open().do_close(flush=False)
    io.flush.assert_not_called()


def test_get_block(stub_local_file):
    # Expect: Read file
    stub_local_file.do_open().io.write(b"1234567890")
    stub_local_file.io.seek(0)
    assert stub_local_file.get_block() == b"1234567890"

    # Expect: Read specific size from file's current position
    stub_local_file.io.seek(0)
    assert stub_local_file.get_block(5) == b"12345"


def test_get_blocks(stub_local_file):
    # Expect: Read file blocks separated by specific size
    stub_local_file.do_open().io.write(b"1234567890")
    stub_local_file.io.seek(0)
    assert list(stub_local_file.get_blocks(5)) == [b"12345", b"67890"]


def test_io_property(stub_local_file):
    # Expect: Set io after file open
    assert stub_local_file.do_open().io is not None

    # Expect: io is None when file not opened
    assert LocalFile("a.file").io is None


def test_opened_property(stub_local_file):
    # Expect: Return True when file opened
    stub_local_file.do_open()
    assert stub_local_file.opened

    # Expect: Return False when file closed
    stub_local_file.do_close()
    assert not stub_local_file.opened

    # Expect: Return False when file not opened
    assert not LocalFile("a.file").opened
