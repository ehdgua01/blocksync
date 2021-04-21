from blocksync.consts import ByteSizes
from blocksync.status import Blocks, Status


def test_initialize_status():
    # Expect: Initialize all status
    status = Status()
    status.initialize(
        block_size=1_000,
        source_size=1_000,
        destination_size=1_000,
    )
    status._add_block("same")
    status._add_block("diff")
    status.initialize(block_size=10, source_size=10, destination_size=10)
    assert status.block_size == 10
    assert status.source_size == 10
    assert status.destination_size == 10
    assert status.blocks == Blocks(same=0, diff=0, done=0)


def test_add_block():
    # Expect: Add each blocks and calculate done block
    status = Status()
    status._add_block("same")
    status._add_block("same")
    status._add_block("diff")
    assert status.blocks == Blocks(same=2, diff=1, done=3)


def test_get_rate():
    # Expect: Return 0.00 when nothing done
    status = Status()
    assert status.rate == 0.00

    status.initialize(source_size=ByteSizes.MiB * 10, destination_size=ByteSizes.MiB * 10)

    # Expect: Return 50.00 when half done
    status._add_block("same")
    status._add_block("same")
    status._add_block("same")
    status._add_block("diff")
    status._add_block("diff")
    assert status.rate == 50.00

    # Expect: Return 100.00 when all done
    status._add_block("same")
    status._add_block("same")
    status._add_block("same")
    status._add_block("diff")
    status._add_block("diff")
    assert status.rate == 100.00

    # Expect: Return 100.00 when exceeding the total size
    status._add_block("diff")
    assert status.rate == 100.00
