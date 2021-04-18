from __future__ import annotations

from pathlib import Path
from typing import Union

import paramiko

from blocksync.files.interfaces import File

__all__ = ["SFTPFile"]


class SFTPFile(File):
    def __init__(self, path: Union[Path, str], **ssh_options):
        super().__init__(path)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh_client.load_system_host_keys()
        ssh_client.connect(**ssh_options)
        self._ssh: paramiko.SSHClient = ssh_client

    def do_close(self, flush=True) -> SFTPFile:
        if self.ssh_connected:
            super().do_close(flush)
        return self

    def _open(self, mode: str) -> paramiko.SFTPFile:
        if self.ssh_connected and (sftp := self._ssh.open_sftp()):
            return sftp.open(self.path if isinstance(self.path, str) else str(self.path), mode=mode)
        raise ValueError("Cannot open the remote file. Please connect paramiko.SSHClient")

    @property
    def ssh_connected(self) -> bool:
        if transport := self._ssh.get_transport():
            return transport.is_active()
        return False
