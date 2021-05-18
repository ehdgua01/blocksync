from unittest.mock import Mock

import paramiko

from blocksync.sync import (
    _connect_ssh,
    _do_create,
    _get_block_size,
    _get_blocks,
    _get_range,
    _get_remotedev_size,
    _get_size,
    _log,
)


def test_get_block_size():
    assert _get_block_size(1) == 1
    assert _get_block_size("1B") == 1


def test_get_range(fake_status):
    fake_status.src_size += 1
    assert _get_range(1, fake_status) == (0, 1)
    assert _get_range(2, fake_status) == (500, 2)


def test_get_size(source_file, source_content):
    assert _get_size(str(source_file)) == len(source_content)


def test_remotedev_size():
    stub_stdin = Mock()
    stub_stdout = Mock(readline=Mock(return_value=10))
    stub_ssh_client = Mock(exec_command=Mock(return_value=(stub_stdin, stub_stdout, Mock())))
    assert 10 == _get_remotedev_size(stub_ssh_client, "command", "path")
    stub_stdin.write.assert_called_once_with("path\n")
    stub_stdout.readline.assert_called_once()
    stub_stdin.close.assert_called_once()
    stub_stdout.close.assert_called_once()


def test_do_create(pytester):
    path = pytester.path / "new.file"
    _do_create(str(path), 10)
    assert path.exists()
    assert _get_size(str(path)) == 10


def test_get_blocks(pytester):
    path = pytester.path / "new.file"
    _do_create(str(path), 20)
    file_data = path.read_bytes()
    with open(path, "rb") as f:
        read_data = list(_get_blocks(f, 10))
        assert read_data[0] == file_data[:10]
        assert read_data[1] == file_data[10:]


def test_log(mocker):
    mock_logger = mocker.patch("blocksync.sync.logger")
    _log(1, "test", 10)
    mock_logger.log(10, f"[Worker {1}] test")


def test_connect_ssh(mocker):
    mock_ssh_client = mocker.patch("blocksync.sync.paramiko.SSHClient")()
    _connect_ssh(
        hostname="hostname",
        password="password",
    )
    mock_ssh_client.set_missing_host_key_policy.assert_called_once_with(paramiko.AutoAddPolicy)
    mock_ssh_client.load_system_host_keys.assert_called_once()
    mock_ssh_client.connect.assert_called_once_with(
        hostname="hostname",
        password="password",
        compress=True,
    )

    mock_ssh_client.reset_mock()
    _connect_ssh(allow_load_system_host_keys=False)
    mock_ssh_client.load_system_host_keys.assert_not_called()
