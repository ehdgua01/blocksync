from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import paramiko

from blocksync.consts import SSH_PORT
from blocksync.files.interfaces import File


class SFTPFile(File):
    def __init__(
        self,
        path: Union[Path, str],
        hostname: str = None,
        port: int = SSH_PORT,
        username: str = None,
        password: str = None,
        key_filename: Union[Path, str] = None,
        compress: bool = True,
        disabled_algorithms: Optional[List[str]] = None,
    ):
        super().__init__(path)
        self.ssh_options: Dict[str, Any] = {
            "hostname": hostname,
            "port": port,
            "username": username,
            "password": password,
            "key_filename": key_filename,
            "compress": compress,
            "disabled_algorithms": disabled_algorithms,
        }
        self._ssh: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def do_close(self, flush=True) -> SFTPFile:
        if self.ssh_connected and self.opened:
            if flush:
                self.io.flush()  # type: ignore[union-attr]
            self.io.close()  # type: ignore[union-attr]
            self.close_connections()
        return self

    def open_sftp(self, session: paramiko.SSHClient = None) -> SFTPFile:
        if session:
            transport: Optional[paramiko.Transport] = session.get_transport()
            if not (transport and transport.is_active()):
                raise ValueError("This session does not connected")
            self._ssh = session
        elif not self.ssh_connected:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            self._ssh.load_system_host_keys()
            self._ssh.connect(**self.ssh_options)
        self._sftp = self._ssh.open_sftp()  # type: ignore[union-attr]
        return self

    def close_connections(self) -> SFTPFile:
        if self.ssh_connected:
            if self._sftp:
                self._sftp.close()
            self._ssh.close()  # type: ignore[union-attr]
        return self

    def _open(self, mode: str) -> paramiko.SFTPFile:
        if not self.ssh_connected:
            self.open_sftp()
        return self._sftp.open(  # type: ignore[union-attr]
            self.path if isinstance(self.path, str) else str(self.path),
            mode=mode,
        )

    @property
    def ssh_connected(self) -> bool:
        if not self._ssh:
            return False
        if transport := self._ssh.get_transport():
            return transport.is_active()
        return False
