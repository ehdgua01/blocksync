import hashlib
import logging
import pathlib
import signal
import unittest
import unittest.mock
from contextlib import contextmanager

from blocksync import File, Syncer
from blocksync.consts import UNITS
from blocksync.utils import generate_random_data


class TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.source = File("source.file")
        self.destination = File("destination.file")
        self.syncer = Syncer(self.source, self.destination)

    def tearDown(self) -> None:
        pathlib.Path(self.source.path).unlink(missing_ok=True)
        pathlib.Path(self.destination.path).unlink(missing_ok=True)

    def create_source_file(self, size: int) -> None:
        self.source.do_create(size)
        self.source.do_open().execute("write", generate_random_data(size).encode()).execute("flush")
        self.source.do_close()

    @contextmanager
    def timeout(self, time):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(time)
        try:
            yield
        except TimeoutError:
            pass
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_IGN)

    def raise_timeout(self, signum, frame) -> None:
        raise TimeoutError()

    def test_set_source(self) -> None:
        self.assertEqual(self.syncer.set_source(self.source), self.syncer)
        self.assertEqual(self.syncer.source, self.source)

    def test_set_destination(self) -> None:
        self.assertEqual(self.syncer.set_destination(self.destination), self.syncer)
        self.assertEqual(self.syncer.destination, self.destination)

    def test_set_callbacks(self) -> None:
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
            self.syncer.set_callbacks(before=before, after=after, monitor=monitor, on_error=on_error),
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

        algorithms = ["sha256", "md5", "blake2b"]
        self.assertEqual(self.syncer.set_hash_algorithms(algorithms), self.syncer)
        self.assertEqual(self.syncer.hash_algorithms, [getattr(hashlib, algo) for algo in algorithms])
        self.create_source_file(10)
        self.syncer.set_source(self.source).set_destination(self.destination).start_sync(create=True, wait=True)
        self.assertEqual(self.syncer.blocks, {"size": 10, "same": 0, "diff": 1, "done": 1})

    def test_set_logger(self) -> None:
        logger = logging.Logger(__name__)
        self.syncer.set_logger(logger)
        self.assertEqual(self.syncer._logger, logger)

    def test_start_sync(self) -> None:
        mock_before = unittest.mock.MagicMock()
        mock_after = unittest.mock.MagicMock()
        mock_monitor = unittest.mock.MagicMock()
        self.assertEqual(
            self.syncer.set_callbacks(before=mock_before, after=mock_after, monitor=mock_monitor),
            self.syncer,
        )

        size = UNITS["MiB"] * 10
        self.create_source_file(size)

        self.assertTrue(
            self.syncer.set_hash_algorithms(["sha256"])
            .start_sync(workers=5, block_size=UNITS["MiB"], interval=0, create=True)
            .started,
        )
        self.assertFalse(self.syncer.finished)
        self.assertEqual(self.syncer.wait(), self.syncer)
        self.assertTrue(self.syncer.finished)
        self.assertEqual(self.syncer.blocks, {"size": size, "same": 0, "diff": 10, "done": 10})
        mock_before.assert_called_with(self.syncer.blocks)
        mock_after.assert_called_with(self.syncer.blocks)
        mock_monitor.assert_called_with(self.syncer.blocks)

        self.assertEqual(
            self.source.do_open().execute_with_result("read"),
            self.destination.do_open().execute_with_result("read"),
        )

        self.assertTrue(
            self.syncer.set_hash_algorithms(["sha256"])
            .start_sync(workers=5, block_size=UNITS["MiB"], interval=0, wait=True)
            .started,
        )
        self.assertEqual(self.syncer.blocks, {"size": size, "same": 10, "diff": 0, "done": 10})
        self.source.do_close()
        self.destination.do_close()

    def test_cancel_sync(self) -> None:
        self.create_source_file(1000)
        with unittest.mock.patch.object(self.syncer, "_add_block") as mock_add_block:
            self.assertEqual(
                self.syncer.set_source(self.source).set_destination(self.destination).cancel(),
                self.syncer,
            )
            self.syncer.start_sync(wait=True, create=True)
            mock_add_block.assert_not_called()

    def test_get_rate(self) -> None:
        self.create_source_file(10)
        self.assertEqual(self.syncer.get_rate(), 0.00)
        self.syncer.set_source(self.source).set_destination(self.destination).start_sync(wait=True, create=True)
        self.assertEqual(self.syncer.get_rate(), 100.00)

    def test_dryrun(self) -> None:
        self.create_source_file(10)
        self.syncer.set_source(self.source).set_destination(self.destination).start_sync(
            dryrun=True, wait=True, create=True
        )
        self.assertEqual(self.syncer.blocks, {"size": 10, "same": 0, "diff": 1, "done": 1})
        self.assertNotEqual(
            self.source.do_open().execute_with_result("read"),
            self.destination.do_open().execute_with_result("read"),
        )

    def test_suspend_and_resume(self) -> None:
        self.create_source_file(10)
        with unittest.mock.patch.object(self.syncer._logger, "info") as mock_logger_info:
            with self.timeout(3):
                self.syncer.set_source(self.source).set_destination(self.destination).start_sync(create=True)
                self.assertEqual(
                    self.syncer.suspend(),
                    self.syncer,
                )
                self.syncer.wait()
            mock_logger_info.assert_called_with("[Worker {}]: Suspending...".format(1))
            self.assertEqual(self.syncer.resume(), self.syncer)
            self.syncer.wait()
            self.assertEqual(self.syncer.blocks, {"size": 10, "same": 0, "diff": 1, "done": 1})
