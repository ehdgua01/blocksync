import logging
import os
from unittest.mock import Mock, call

import pytest

from blocksync.worker import Worker


@pytest.fixture(autouse=True)
def mock_time(mocker):
    return mocker.patch("blocksync.worker.time")


@pytest.fixture
def stub_worker(mocker):
    worker = Worker(
        worker_id=1,
        syncer=Mock(canceled=False),
        startpos=0,
        endpos=5,
        dryrun=False,
        sync_interval=1,
        monitoring_interval=1,
        logger=Mock(),
    )
    mocker.patch("blocksync.worker.timer", side_effect=[0, 1, 1.5, 2, 3])
    worker.syncer.status.block_size = 2
    worker.syncer.src.io.tell.side_effect = [1, 2, 4, 5]  # type: ignore[union-attr]
    worker.syncer.src.get_blocks.return_value = [b"1", b"2", b"33", b"5"]  # type: ignore[attr-defined]
    worker.syncer.dest.get_blocks.return_value = [b"1", b"2", b"44", b"6"]  # type: ignore[attr-defined]
    return worker


def test_run(stub_worker):
    stub_worker._sync = Mock()
    stub_worker.run()
    stub_worker.syncer.hooks.run_root_before.assert_called_once()
    stub_worker.syncer.hooks.run_root_after.assert_called_once()
    stub_worker._sync.assert_called_once()
    stub_worker.syncer.src.do_close.assert_called_once()
    stub_worker.syncer.dest.do_close.assert_called_once()


def test_sync(stub_worker, mock_time):
    stub_worker._sync()
    stub_worker.syncer.src.do_open.return_value.io.seek.assert_called_once_with(stub_worker.startpos)
    stub_worker.syncer.dest.do_open.return_value.io.seek.assert_called_once_with(stub_worker.startpos)
    stub_worker.syncer.hooks.run_before.assert_called_once()

    stub_worker.syncer.status._add_block.assert_has_calls([call("same"), call("same"), call("diff")])

    stub_worker.syncer.dest.io.seek.assert_has_calls([call(-2, os.SEEK_CUR), call(-1, os.SEEK_CUR)])
    stub_worker.syncer.dest.io.write.assert_has_calls([call(b"33"), call(b"5")])
    assert stub_worker.syncer.dest.io.flush.call_count == 2

    stub_worker.syncer.hooks.run_monitor.assert_has_calls(
        [
            call(stub_worker.syncer.status),
            call(stub_worker.syncer.status),
            call(stub_worker.syncer.status),
        ]
    )

    mock_time.sleep.assert_has_calls([call(1), call(1), call(1)])

    stub_worker.logger.log.assert_has_calls(
        [
            call(
                logging.INFO,
                f"[Worker 1]: Start sync(startpos: 0, endpos: 5) {stub_worker.syncer.src} to {stub_worker.syncer.dest}",
            ),
            call(logging.INFO, "[Worker 1]: !!! Done !!!"),
        ]
    )

    stub_worker.syncer.hooks.run_after.assert_called_once_with(stub_worker.syncer.status)


def test_sync_with_suspending(stub_worker):
    stub_worker.syncer.suspended.is_set.return_value = False
    stub_worker._sync()
    stub_worker.logger.log.assert_has_calls([call(logging.INFO, "[Worker 1]: Suspending...")])
    stub_worker.syncer.suspended.wait.assert_called()


def test_sync_with_canceling(stub_worker):
    stub_worker.syncer.canceled = True
    stub_worker._sync()
    stub_worker.logger.log.assert_has_calls([call(logging.INFO, "[Worker 1]: Synchronization task has been canceled")])


def test_run_on_error(stub_worker):
    expected_error = OSError("Error raised when writing data")
    stub_worker.syncer.dest.io.write.side_effect = expected_error
    stub_worker._sync()
    stub_worker.syncer.hooks.run_on_error.assert_called_once_with(expected_error, stub_worker.syncer.status)
    stub_worker.logger.log.assert_has_calls(
        [call(logging.ERROR, "[Worker 1]: Error raised when writing data", exc_info=True)]
    )


def test_log(stub_worker):
    # Expect: Call logger.log with message, level, additional arguments
    stub_worker._log("test", logging.DEBUG, 1, exc_info=True)
    stub_worker.logger.log.assert_called_once_with(logging.DEBUG, "[Worker 1]: test", 1, exc_info=True)
