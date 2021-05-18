from unittest.mock import Mock

import pytest

from blocksync._hooks import Hooks


@pytest.fixture
def stub_hooks():
    return Hooks(Mock(), Mock(), Mock(), Mock())


def test_run_before(stub_hooks):
    stub_hooks.run_before()
    stub_hooks.before.assert_called_once()


def test_run_after(stub_hooks, fake_status):
    stub_hooks.run_after(fake_status)
    stub_hooks.after.assert_called_once_with(fake_status)


def test_run_monitor(stub_hooks, fake_status):
    stub_hooks.run_monitor(fake_status)
    stub_hooks.monitor.assert_called_once_with(fake_status)


def test_run_on_error(stub_hooks, fake_status):
    exc = Exception()
    stub_hooks.run_on_error(exc, fake_status)
    stub_hooks.on_error.assert_called_once_with(exc, fake_status)
