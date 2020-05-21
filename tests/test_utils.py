import unittest

from blocksync.utils import validate_callback, generate_random_data


class TestCase(unittest.TestCase):
    def test_validate_callback(self) -> None:
        def func(a, b, c):
            pass

        self.assertEqual(validate_callback(func, 3), True)

        with self.assertRaises(ValueError):
            # If you need a function that requires 4 arguments
            validate_callback(func, 4)

        with self.assertRaises(TypeError):
            validate_callback("only callback function", 3)

    def test_generate_random_data(self) -> None:
        random_data = generate_random_data(100)
        self.assertEqual(len(random_data), 100)
        self.assertTrue(isinstance(random_data, str))
