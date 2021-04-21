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


@pytest.fixture
def stub_sftp_client(stub_ssh_client):
    return stub_ssh_client.open_sftp.return_value


def test_target_file_is_a_block_device(mocker, stub_ssh_client, stub_sftp_client):
    # When: The target file is a block device
    stub_ssh_client.exec_command.return_value = (Mock(), Mock(read=Mock(return_value=b"10")), Mock())
    mocker.patch("blocksync.files.sftp_file.File._get_size", return_value=0)
    stub_sftp_client.open.return_value.stat.return_value.st_mode = 25008
    file = SFTPFile("filepath")

    # Then: Use a special command to get the size of the block device
    assert file.do_open().size == 10
    stub_ssh_client.exec_command.assert_called_once_with(
        """python -c "with open('filepath', 'r') as f: f.seek(0, 2); print(f.tell())" """
    )

    # And: Return if already got the size
    mocker.patch("blocksync.files.sftp_file.File._get_size", return_value=1)
    assert file.do_open().size == 1


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

    # Expect: Return False when SSH hasn't transport
    stub_ssh_client.get_transport.return_value = None
    assert not file.ssh_connected
