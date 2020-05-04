from pathlib import PurePath
from typing import Tuple, IO, Any, Union, Dict

import paramiko

from blocksync.consts import SSH_PORT


class File(object):
    def __init__(
        self,
        path: Union[PurePath, str],
        mode: str,
        create: bool = False,
        remote: bool = False,
        hostname: str = None,
        port: int = SSH_PORT,
        username: str = None,
        password: str = None,
        key_filename: Union[PurePath, str] = "",
        compress: bool = True,
        cipher: str = "aes128-ctr",
    ):
        __paramiko_ciphers = paramiko.Transport._preferred_ciphers

        if cipher not in __paramiko_ciphers:
            raise ValueError("Invalid ssh encryption algorithms")

        self._path = path
        self._mode = mode
        self._create = create
        self._remote = remote
        self._remote_options: Dict[str, Any] = {
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
        self._ssh = Union[paramiko.SSHClient, None] = None
        self._sftp: Union[paramiko.SFTPClient, None] = None

    def connect(self, session: paramiko.SSHClient = None):
        if self.connected:
            return

        if not session:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            self._ssh.load_system_host_keys()
            self._ssh.connect(**self._remote_options)
        else:
            self._ssh = session
        self._sftp = self._ssh.open_sftp()

    def close(self):
        if isinstance(self._ssh, paramiko.SSHClient):
            self._ssh.close()

    def do_create(self, size: int) -> None:
        if self._remote:
            if not self.connected:
                self.connect()

            open_ = self._sftp.open
        else:
            open_ = open

        with open_(self._path, mode="w") as f:
            f.truncate(size)

    def do_open(self, path: str, mode: str) -> Tuple[IO, int]:
        pass

    def get_blocks(self) -> Any:
        pass

    @property
    def connected(self) -> bool:
        return isinstance(self._sftp, paramiko.SFTPClient)
