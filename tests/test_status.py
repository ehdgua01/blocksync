from blocksync._consts import ByteSizes
from blocksync._status import Blocks


def test_initialize_status(fake_status):
    # Expect: Set chunk size
    assert fake_status.chunk_size == fake_status.src_size // fake_status.workers


def test_add_block(fake_status):
    # Expect: Add each blocks and calculate done block
    fake_status.add_block("same")
    fake_status.add_block("same")
    fake_status.add_block("diff")
    assert fake_status.blocks == Blocks(same=2, diff=1, done=3)


def test_get_rate(fake_status):
    # Expect: Return 0.00 when nothing done
    assert fake_status.rate == 0.00

    fake_status.block_size = ByteSizes.MiB
    fake_status.src_size = fake_status.dest_size = ByteSizes.MiB * 10

    # Expect: Return 50.00 when half done
    fake_status.add_block("same")
    fake_status.add_block("same")
    fake_status.add_block("same")
    fake_status.add_block("diff")
    fake_status.add_block("diff")
    assert fake_status.rate == 50.00

    # Expect: Return 100.00 when all done
    fake_status.add_block("same")
    fake_status.add_block("same")
    fake_status.add_block("same")
    fake_status.add_block("diff")
    fake_status.add_block("diff")
    assert fake_status.rate == 100.00

    # Expect: Return 100.00 when exceeding the total size
    fake_status.add_block("diff")
    assert fake_status.rate == 100.00
