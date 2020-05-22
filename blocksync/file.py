import os
import threading
from pathlib import PurePath
from typing import Any, Union, Dict, IO

import paramiko

from blocksync.consts import SSH_PORT, UNITS

__all__ = ["File"]


class File(object):
    def __init__(
        self,
        path: Union[PurePath, str],
        start_pos: int = os.SEEK_SET,
        remote: bool = False,
        hostname: str = None,
        port: int = SSH_PORT,
        username: str = None,
        password: str = None,
        key_filename: Union[PurePath, str] = None,
        compress: bool = True,
        cipher: str = "aes128-ctr",
    ) -> None:
        __paramiko_ciphers = paramiko.Transport._preferred_ciphers

        if remote and (cipher not in __paramiko_ciphers):
            raise ValueError("Invalid ssh encryption algorithm")

        self.path = path
        self.start_pos = start_pos
        self.remote = remote
        self.ssh_options: Dict[str, Any] = {
            "hostname": hostname,
            "port": port,
            "username": username,
            "password": password,
            "key_filename": key_filename,
            "compress": compress,
            "disabled_algorithms": {
                "cipher": [c for c in __paramiko_ciphers if cipher != c]
            },
        }

        self._local = threading.local()

    def __repr__(self):
        return "<blocksync.File path={} state={}>".format(
            self.path, "opened" if self.opened else "closed",
        )

    def open_sftp(self, session: paramiko.SSHClient = None) -> "File":
        if self.connected:
            return self

        if session is None:
            self._local.ssh = paramiko.SSHClient()
            self._local.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            self._local.ssh.load_system_host_keys()
            self._local.ssh.connect(**self.ssh_options)
        elif not isinstance(session, paramiko.SSHClient):
            raise ValueError("Session isn't instance of paramiko.SSHClient")
        elif session.get_transport() is None or not session.get_transport().is_active():
            raise ValueError("This session is not connected")
        else:
            self._local.ssh = session

        self._local.sftp = self._local.ssh.open_sftp()
        return self

    def close_sftp(self) -> "File":
        if self.connected:
            self._local.sftp.close()
            self._local.ssh.close()
        return self

    def do_create(self, size: int = 0) -> "File":
        with self._open(mode="w") as f:
            f.truncate(size or self.size)
        return self

    def do_open(self) -> "File":
        if self.opened:
            return self

        self._local.io = self._open(mode="rb+")
        self.execute("seek", os.SEEK_SET)
        return self

    def do_close(self, flush=True, close_sftp=True) -> "File":
        if self.opened:
            if flush:
                self._local.io.flush()
            self._local.io.close()

        if self.remote and self.connected and close_sftp:
            self.close_sftp()
        return self

    def get_blocks(self, block_size: int = UNITS["MiB"]) -> Any:
        while self.opened:
            if block := self._local.io.read(block_size):
                yield block
            else:
                break  # pragma: no cover

    def execute(self, operation, *args, **kwargs) -> "File":
        self._execute(operation, *args, **kwargs)
        return self

    def execute_with_result(self, operation, *args, **kwargs) -> Any:
        return self._execute(operation, *args, **kwargs)

    def _execute(self, operation, *args, **kwargs) -> Any:
        if not self.opened:
            raise AttributeError("File is not opened")

        return getattr(self._local.io, operation)(*args, **kwargs)

    def _open(self, mode: str) -> IO:
        if self.remote:
            if not self.connected:
                self.open_sftp()
            return self._local.sftp.open(self.path, mode=mode)
        else:
            return open(self.path, mode=mode)

    @property
    def connected(self) -> bool:
        if (
            hasattr(self._local, "ssh")
            and isinstance(self._local.ssh, paramiko.SSHClient)
            and self._local.ssh.get_transport() is not None
        ):
            return self._local.ssh.get_transport().is_active()
        return False

    @property
    def opened(self) -> bool:
        if hasattr(self._local, "io"):
            if hasattr(self._local.io, "_closed"):
                return not self._local.io._closed
            return not self._local.io.closed
        return False

    @property
    def size(self) -> int:
        if self.remote:
            _stat = self._local.sftp.stat
        else:
            _stat = os.stat
        return _stat(self.path).st_size
