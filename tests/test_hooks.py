from unittest.mock import Mock

from blocksync.hooks import Hooks


def test_run_before():
    hook = Hooks()
    hook.before = Mock()
    hook.run_before()
    hook.before.assert_called_once()


def test_run_after(fake_status):
    hook = Hooks()
    hook.after = Mock()
    hook.run_after(fake_status)
    hook.after.assert_called_once_with(fake_status)


def test_run_monitor(fake_status):
    hook = Hooks()
    hook.monitor = Mock()
    hook.run_monitor(fake_status)
    hook.monitor.assert_called_once_with(fake_status)


def test_run_on_error(fake_status):
    hook = Hooks()
    hook.on_error = Mock()
    exc = Exception()
    hook.run_on_error(exc, fake_status)
    hook.on_error.assert_called_once_with(exc, fake_status)
