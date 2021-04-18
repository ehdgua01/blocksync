import unittest

from blocksync.utils import generate_random_data


class TestCase(unittest.TestCase):
    def test_generate_random_data(self) -> None:
        random_data = generate_random_data(100)
        self.assertEqual(len(random_data), 100)
        self.assertTrue(isinstance(random_data, str))
