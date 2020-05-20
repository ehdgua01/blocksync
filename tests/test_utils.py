import unittest

from blocksync.utils import validate_callback


class TestCase(unittest.TestCase):
    def test_validate_callback(self):
        def func(a, b, c):
            pass

        self.assertEqual(validate_callback(func, 3), func)

        with self.assertRaises(TypeError):
            # If you need a function that requires 4 arguments
            validate_callback(func, 4)

        with self.assertRaises(TypeError):
            validate_callback("only callback function", 3)
