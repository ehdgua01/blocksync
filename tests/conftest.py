import pytest

from blocksync._status import Status

pytest_plugins = "pytester"


@pytest.fixture
def fake_status():
    return Status(
        workers=2,
        block_size=500,
        src_size=1_000,
        dest_size=1_000,
    )


@pytest.fixture(scope="session")
def source_content():
    return b"source content"


@pytest.fixture
def source_file(pytester, source_content):
    return pytester.makefile(".img", source_content)
