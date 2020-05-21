import unittest
import unittest.mock
import logging
import pathlib

from blocksync import Syncer, File
from blocksync.utils import generate_random_data
from blocksync.consts import UNITS


class TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.syncer = Syncer()
        self.source = File("source.file")
        self.destination = File("destination.file")

    def tearDown(self) -> None:
        pathlib.Path(self.source.path).unlink(missing_ok=True)
        pathlib.Path(self.destination.path).unlink(missing_ok=True)

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
                    self.syncer.set_callbacks(**{callback: "xxx"})

                with self.assertRaises(ValueError):
                    self.syncer.set_callbacks(**{callback: lambda: None})

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
        for logger in ["xxx", object]:
            with self.subTest():
                with self.assertRaises(TypeError):
                    self.syncer.set_logger(logger)

        # possible to pass class by argument.
        # but the logger will be named by __name__
        self.assertEqual(self.syncer.set_logger(logging.Logger), self.syncer)

        self.assertEqual(self.syncer.set_logger(logging.Logger(__name__)), self.syncer)

    def test_start_sync(self) -> None:
        with self.assertRaises(AttributeError):
            self.syncer.start_sync()

        self.syncer.set_source(self.source)

        with self.assertRaises(AttributeError):
            self.syncer.start_sync()

        self.syncer.set_destination(self.destination)

        with self.assertRaises(TypeError):
            self.syncer.start_sync(interval="xxx")

        with self.assertRaises(TypeError):
            self.syncer.start_sync(pause="xxx")

        size = UNITS["MiB"] * 10
        self.source.do_create(size)
        self.destination.do_create(size)
        self.source.do_open().execute(
            "write", generate_random_data(size).encode()
        ).execute("flush")
        self.source.do_close()
        self.destination.do_close()

        mock_before = unittest.mock.MagicMock()
        mock_after = unittest.mock.MagicMock()
        mock_monitor = unittest.mock.MagicMock()

        self.assertEqual(
            self.syncer.set_callbacks(
                before=mock_before, after=mock_after, monitor=mock_monitor
            ),
            self.syncer,
        )
        self.assertEqual(self.syncer.start_sync(interval=0).started, True)
        self.assertEqual(self.syncer.wait(), self.syncer)
        self.assertEqual(self.syncer.finished, True)
        self.assertEqual(
            self.syncer.blocks, {"size": size, "same": 0, "diff": 10, "done": 10}
        )
        mock_before.assert_called()
        mock_after.assert_called()
        mock_monitor.assert_called()
