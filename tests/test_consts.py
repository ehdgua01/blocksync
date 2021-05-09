from blocksync._consts import ByteSizes


def test_parse_readable_byte_size():
    assert ByteSizes.MiB == ByteSizes.parse_readable_byte_size("1_048_576")

    assert ByteSizes.MiB == ByteSizes.parse_readable_byte_size("1M")
    assert ByteSizes.M == ByteSizes.parse_readable_byte_size("1M")
