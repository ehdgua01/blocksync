from pathlib import Path
from unittest.mock import Mock

import paramiko
import pytest

from blocksync import SFTPFile


@pytest.fixture(autouse=True)
def stub_ssh_client(mocker):
    ssh_client = mocker.patch(
        "blocksync.files.sftp_file.paramiko.SSHClient",
        Mock(get_transport=Mock(return_value=Mock(is_active=Mock(return_value=True)))),
    )
    return ssh_client.return_value


def test_do_close(mocker, stub_ssh_client):
    # Expect: Close only when ssh connected
    mock_do_close = mocker.patch("blocksync.files.sftp_file.File.do_close")
    file = SFTPFile("")
    file.do_close()
    stub_ssh_client.get_transport.return_value.is_active.return_value = False
    file.do_close()
    mock_do_close.assert_called_once_with(True)


def test_open(stub_ssh_client):
    # Expect: Open without error even if path argument is an instance of pathlib.Path
    file = SFTPFile(Path("test"))
    file._open("r")
    stub_ssh_client.open_sftp.return_value.open.assert_called_once_with("test", mode="r")


def test_raise_error_when_ssh_not_connected(stub_ssh_client):
    # Expect: Raise error when ssh not connected
    file = SFTPFile("")
    stub_ssh_client.get_transport.return_value.is_active.return_value = False
    with pytest.raises(ValueError, match="Cannot open the remote file. Please connect paramiko.SSHClient"):
        file._open("r")


def test_call_setup_methods(stub_ssh_client):
    # Expect: Call paramiko setup methods
    SFTPFile("")
    stub_ssh_client.set_missing_host_key_policy.assert_called_once_with(paramiko.AutoAddPolicy)
    stub_ssh_client.load_system_host_keys.assert_called_once()


def test_pass_ssh_config(stub_ssh_client):
    # Expect: Connect SSH using passed arguments
    SFTPFile("", hostname="test", password="test")
    stub_ssh_client.connect.assert_called_once_with(hostname="test", password="test")


def test_ssh_connected(stub_ssh_client):
    # Expect: Return True when SSH connected
    file = SFTPFile("")
    assert file.ssh_connected

    # Expect: Return False when SSH not connected
    stub_ssh_client.get_transport.return_value.is_active.return_value = False
    assert not file.ssh_connected
