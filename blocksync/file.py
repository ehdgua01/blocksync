import os
from pathlib import PurePath
from typing import Any, Union, Dict, IO

import paramiko

from blocksync.consts import SSH_PORT, UNITS


class File(object):
    def __init__(
        self,
        path: Union[PurePath, str],
        block_size: int = UNITS["MiB"],
        start_pos: int = os.SEEK_SET,
        remote: bool = False,
        hostname: str = None,
        port: int = SSH_PORT,
        username: str = None,
        password: str = None,
        key_filename: Union[PurePath, str] = "",
        compress: bool = True,
        cipher: str = "aes128-ctr",
    ) -> None:
        __paramiko_ciphers = paramiko.Transport._preferred_ciphers

        if remote and (cipher not in __paramiko_ciphers):
            raise ValueError("Invalid ssh encryption algorithm")

        self.path = path
        self.block_size = block_size
        self.start_pos = start_pos
        self.size: int = 0
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

        self._io: Union[IO, None] = None
        self._ssh = Union[paramiko.SSHClient, None] = None
        self._sftp: Union[paramiko.SFTPClient, None] = None

    def __str__(self):
        return "<blocksync.File path={} block_size={} start_pos={} state={}>".format(
            self.path,
            self.block_size,
            self.start_pos,
            "opened" if self.opened else "closed",
        )

    def __repr__(self):
        return "<blocksync.File path={} block_size={} start_pos={} state={}>".format(
            self.path,
            self.block_size,
            self.start_pos,
            "opened" if self.opened else "closed",
        )

    def open_sftp(self, session: paramiko.SSHClient = None) -> "File":
        if self.connected:
            return self

        if session is None:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            self._ssh.load_system_host_keys()
            self._ssh.connect(**self.ssh_options)
        elif isinstance(session, paramiko.SSHClient):
            self._ssh = session
        else:
            raise ValueError("Session isn't instance of paramiko.SSHClient")

        self._sftp = self._ssh.open_sftp()
        return self

    def close_sftp(self) -> "File":
        if isinstance(self._ssh, paramiko.SSHClient) and self.connected:
            self._ssh.close()
        return self

    def do_create(self, size: int = 0) -> "File":
        with self._open(mode="w") as f:
            f.truncate(size or self.size)
        return self

    def do_open(self) -> "File":
        if self.opened:
            self.do_close()

        self._io = self._open(mode="rb+")
        self._io.seek(os.SEEK_SET, os.SEEK_END)
        self.size = self._io.tell()
        self._io.seek(self.start_pos)
        return self

    def do_close(self, flush=True) -> "File":
        try:
            if self.opened:
                if flush:
                    self._io.flush()
                self._io.close()

            if self.remote and self.connected:
                self.close_sftp()
        except:
            pass
        return self

    def get_blocks(self) -> Any:
        while self.opened:
            if block := self._io.read(self.block_size):
                yield block
            else:
                break

    def write(self, data: Any) -> "File":
        self._io.write(data)
        self._io.flush()
        return self

    def seek(self, offset: int, whence: int = 0) -> "File":
        self._io.seek(offset, whence)
        return self

    def _open(self, mode: str) -> IO:
        if self.remote:
            if not self.connected:
                self.open_sftp()
            return self._sftp.open(self.path, mode=mode)
        else:
            return open(self.path, mode=mode)

    @property
    def connected(self) -> bool:
        if isinstance(self._ssh, paramiko.SSHClient) and self._ssh.get_transport():
            return self._ssh.get_transport().is_active()
        return False

    @property
    def opened(self) -> bool:
        try:
            self._io.tell()
            return True
        except:
            return False
