from unittest.mock import Mock

from blocksync._sync_manager import SyncManager


def test_cancel_sync():
    manager = SyncManager()
    assert not manager.canceled

    manager.cancel_sync()
    assert manager.canceled


def test_wait_sync():
    mock_worker1, mock_worker2 = Mock(), Mock()
    manager = SyncManager()
    manager.workers.append(mock_worker1)
    manager.workers.append(mock_worker2)
    manager.wait_sync()
    mock_worker1.join.assert_called_once()
    mock_worker2.join.assert_called_once()


def test_suspend_and_resume():
    manager = SyncManager()
    manager.suspend()
    assert manager.suspended

    manager.resume()
    assert not manager.suspended

    manager._suspend = Mock()
    manager._wait_resuming()
    manager._suspend.wait.assert_called_once()


def test_finished():
    worker = Mock()
    worker.is_alive.return_value = False
    manager = SyncManager()
    manager.workers.append(worker)
    assert manager.finished

    worker.is_alive.return_value = True
    assert not manager.finished
