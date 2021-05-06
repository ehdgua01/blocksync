import pytest

from blocksync._status import Status


@pytest.fixture
def fake_status():
    return Status(
        workers=1,
        block_size=1_000,
        src_size=1_000,
        dest_size=1_000,
    )
