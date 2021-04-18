from unittest.mock import Mock

import pytest

from blocksync.hooks import Hooks
from blocksync.status import Blocks


@pytest.fixture
def stub_blocks():
    return Blocks(same=0, diff=0, done=0)


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


def test_run_root_after(stub_blocks):
    hook = Hooks()
    hook.root_after = Mock()
    hook.run_root_after(stub_blocks)
    hook.root_after.assert_called_once_with(stub_blocks)


def test_run_after(stub_blocks):
    hook = Hooks()
    hook.after = Mock()
    hook.run_after(stub_blocks)
    hook.after.assert_called_once_with(stub_blocks)


def test_run_monitor(stub_blocks):
    hook = Hooks()
    hook.monitor = Mock()
    hook.run_monitor(stub_blocks)
    hook.monitor.assert_called_once_with(stub_blocks)


def test_run_on_error(stub_blocks):
    hook = Hooks()
    hook.on_error = Mock()
    exc = Exception()
    hook.run_on_error(exc, stub_blocks)
    hook.on_error.assert_called_once_with(exc, stub_blocks)
