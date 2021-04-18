from blocksync.utils import generate_random_data


def test_generate_random_data():
    random_data = generate_random_data(100)
    assert len(random_data) == 100
