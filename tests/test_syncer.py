import unittest
import logging

from blocksync import Syncer
from blocksync import File


class TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.syncer = Syncer()

    def test_set_source(self) -> None:
        with self.assertRaises(TypeError):
            self.syncer.set_source("")

        source = File("source.file")
        self.assertEqual(self.syncer.set_source(source), self.syncer)
        self.assertEqual(self.syncer.source, source)

    def test_set_destination(self) -> None:
        with self.assertRaises(TypeError):
            self.syncer.set_destination("")

        destination = File("destination.file")
        self.assertEqual(self.syncer.set_destination(destination), self.syncer)
        self.assertEqual(self.syncer.destination, destination)

    def test_set_callbacks(self) -> None:
        for callback in ["before", "after", "monitor", "on_error"]:
            with self.subTest():
                with self.assertRaises(TypeError):
                    self.syncer.set_callbacks(
                        **{callback: "xxx",}
                    )

                with self.assertRaises(ValueError):
                    self.syncer.set_callbacks(
                        **{callback: lambda: None,}
                    )

        # before callback least requires 1 argument
        def before(x):
            return x

        # after callback least requires 1 argument
        def after(x):
            return x

        # monitor callback least requires 1 argument
        def monitor(x):
            return x

        # on_error callback least requires 2 argument
        def on_error(x, e):
            return x, e

        self.assertEqual(
            self.syncer.set_callbacks(
                before=before, after=after, monitor=monitor, on_error=on_error
            ),
            self.syncer,
        )
        self.assertEqual(self.syncer.before, before)
        self.assertEqual(self.syncer.after, after)
        self.assertEqual(self.syncer.monitor, monitor)
        self.assertEqual(self.syncer.on_error, on_error)

    def test_set_hash_algorithms(self) -> None:
        with self.assertRaises(ValueError):
            # Raise error when hash algorithm not supported by hashlib
            self.syncer.set_hash_algorithms(["xxx"])

        # Does not raise errors even when
        # the type of hash algorithms is not a string array
        self.assertEqual(self.syncer.set_hash_algorithms(""), self.syncer)

        self.assertEqual(self.syncer.set_hash_algorithms(["sha256"]), self.syncer)

    def test_set_logger(self) -> None:
        with self.assertRaises(TypeError):
            self.syncer.set_logger("xxx")

        # possible to pass class by argument.
        # but the logger will be named by __name__
        self.assertEqual(self.syncer.set_logger(logging.Logger), self.syncer)

        self.assertEqual(self.syncer.set_logger(logging.Logger(__name__)), self.syncer)
