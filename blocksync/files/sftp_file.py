from __future__ import annotations

import stat
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

    def _get_size(self, fileobj: paramiko.SFTPFile) -> int:  # type: ignore[override]
        size = super()._get_size(fileobj)
        if size == 0 and stat.S_ISBLK(fileobj.stat().st_mode):  # type: ignore[arg-type]
            stdin, stdout, stderr = self._ssh.exec_command(
                f"""python -c "with open('{self.path}', 'r') as f: f.seek(0, 2); print(f.tell())" """,
            )
            return int(stdout.read())
        return size

    @property
    def ssh_connected(self) -> bool:
        if transport := self._ssh.get_transport():
            return transport.is_active()
        return False
