from unittest.mock import Mock

import pytest

from blocksync.syncer import Syncer


@pytest.fixture(autouse=True)
def mock_worker(mocker):
    return mocker.patch("blocksync.syncer.Worker")


@pytest.fixture
def mock_syncer():
    syncer = Syncer(Mock(), Mock())
    syncer.src.size = syncer.dest.size = 10
    syncer._suspended = Mock()
    syncer.status = Mock()
    syncer.hooks = Mock()
    syncer.logger = Mock()
    return syncer


def test_raise_error_if_worker_less_than_1(mock_syncer):
    with pytest.raises(ValueError, match="Workers must be greater than 1"):
        mock_syncer.start_sync(workers=0)


def test_pre_sync(mock_syncer):
    # Expect: Open both of target files
    mock_syncer.src.size = mock_syncer.dest.size = 10
    mock_syncer._pre_sync()
    mock_syncer.src.do_open.assert_called_once()
    mock_syncer.dest.do_open.assert_called_once()


def test_when_destination_file_does_not_exists(mock_syncer):
    # Expect: Raise error if create is False
    mock_syncer.dest.do_open.side_effect = FileNotFoundError
    with pytest.raises(FileNotFoundError):
        mock_syncer._pre_sync(create=False)

    # Expect: Create an empty file with the size of the source
    mock_syncer._pre_sync(create=True)
    mock_syncer.dest.do_create.assert_called_once_with(10)
    mock_syncer.dest.do_create.return_value.do_open.assert_called_once()


def test_when_src_and_dest_file_size_does_not_same(mock_syncer):
    # Expect: Call info with expected msg
    mock_syncer.src.size = mock_syncer.dest.size - 1
    mock_syncer._pre_sync()
    mock_syncer.logger.info.assert_called_once_with("Source size(9) is less than destination size(10)")

    # Expect: Call warning with expected msg
    mock_syncer.src.size = mock_syncer.dest.size + 1
    mock_syncer._pre_sync()
    mock_syncer.logger.warning.assert_called_once_with("Source size(11) is greater than destination size(10)")


def test_get_positions(mock_syncer):
    # Expect: Return the correct positions
    assert mock_syncer._get_positions(workers=1, worker_id=1) == (0, 10)
    assert mock_syncer._get_positions(workers=2, worker_id=1) == (0, 5)
    assert mock_syncer._get_positions(workers=2, worker_id=2) == (5, 10)
    assert mock_syncer._get_positions(workers=3, worker_id=1) == (0, 3)
    assert mock_syncer._get_positions(workers=3, worker_id=2) == (3, 6)
    assert mock_syncer._get_positions(workers=3, worker_id=3) == (6, 10)


def test_start_sync(mock_syncer, mock_worker):
    mock_syncer._pre_sync = Mock()
    mock_syncer.wait = Mock()
    mock_syncer.start_sync(
        workers=1,
        block_size=1,
        wait=True,
        dryrun=False,
        create=False,
        sync_interval=1,
        monitoring_interval=1,
    )
    assert not mock_syncer.canceled
    mock_syncer._pre_sync.assert_called_once_with(False)
    mock_syncer.status.initialize.assert_called_once_with(block_size=1, source_size=10, destination_size=10)
    mock_syncer._suspended.set.assert_called_once()
    worker_instance = mock_worker.return_value
    mock_worker.assert_called_once_with(
        worker_id=1,
        syncer=mock_syncer,
        startpos=0,
        endpos=10,
        dryrun=False,
        sync_interval=1,
        monitoring_interval=1,
        logger=mock_syncer.logger,
    )
    mock_worker.return_value.start.assert_called_once()
    mock_syncer.wait.assert_called_once()
    assert mock_syncer.workers == [worker_instance]
    assert mock_syncer.started

    # Expect: Create worker instances by number of workers
    mock_syncer.start_sync(
        workers=3,
        block_size=1,
        wait=True,
        dryrun=False,
        create=False,
        sync_interval=1,
        monitoring_interval=1,
    )
    assert mock_syncer.workers == [worker_instance, worker_instance, worker_instance]


def test_finished(mock_syncer, mock_worker):
    # Expect: Return False before start
    assert not mock_syncer.finished
    mock_syncer.start_sync()

    # Expect: Return False if some worker is alive
    mock_worker.return_value.is_alive.return_value = True
    assert not mock_syncer.finished

    # Expect: Return True if all worker finished
    mock_worker.return_value.is_alive.return_value = False
    assert mock_syncer.finished


def test_wait(mock_syncer, mock_worker):
    # Expect: Wait all workers
    mock_worker.return_value.is_alive.return_value = True
    mock_syncer.start_sync(workers=2).wait()
    assert mock_worker.return_value.is_alive.call_count == 2
    assert mock_worker.return_value.join.call_count == 2


def test_cancel(mock_syncer):
    assert mock_syncer.cancel()._canceled


def test_suspend(mock_syncer):
    # Expect: Suspend when not blocking
    mock_syncer._suspended.is_set.return_value = True
    mock_syncer.suspend()
    mock_syncer._suspended.clear.assert_called_once()
    mock_syncer._suspended.reset_mock()

    mock_syncer._suspended.is_set.return_value = False
    mock_syncer.suspend()
    assert mock_syncer.suspended
    mock_syncer._suspended.clear.assert_not_called()


def test_resume(mock_syncer):
    # Expect: Resume when blocking
    mock_syncer._suspended.is_set.return_value = False
    mock_syncer.resume()
    mock_syncer._suspended.set.assert_called_once()
    mock_syncer._suspended.reset_mock()

    mock_syncer._suspended.is_set.return_value = True
    mock_syncer.resume()
    assert not mock_syncer.suspended
    mock_syncer._suspended.set.assert_not_called()
