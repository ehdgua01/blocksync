from unittest.mock import Mock

import pytest

from blocksync.hooks import Hooks
from blocksync.status import Status


@pytest.fixture
def stub_status():
    return Status()


def test_run_root_before():
    hook = Hooks()
    hook.root_before = Mock()
    hook.run_root_before()
    hook.root_before.assert_called_once()


def test_run_before():
    hook = Hooks()
    hook.before = Mock()
    hook.run_before()
    hook.before.assert_called_once()


def test_run_root_after(stub_status):
    hook = Hooks()
    hook.root_after = Mock()
    hook.run_root_after(stub_status)
    hook.root_after.assert_called_once_with(stub_status)


def test_run_after(stub_status):
    hook = Hooks()
    hook.after = Mock()
    hook.run_after(stub_status)
    hook.after.assert_called_once_with(stub_status)


def test_run_monitor(stub_status):
    hook = Hooks()
    hook.monitor = Mock()
    hook.run_monitor(stub_status)
    hook.monitor.assert_called_once_with(stub_status)


def test_run_on_error(stub_status):
    hook = Hooks()
    hook.on_error = Mock()
    exc = Exception()
    hook.run_on_error(exc, stub_status)
    hook.on_error.assert_called_once_with(exc, stub_status)
