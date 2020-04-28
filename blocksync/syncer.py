import os
import time
import logging
from typing import IO, Any, Tuple, Callable, List, Union, DefaultDict, Dict
from collections import defaultdict

import paramiko

from blocksync.consts import FADV, UNITS, SSH_PORT
from blocksync.exception import StopSync

logger = logging.getLogger(__name__)
BlocksType = DefaultDict[str, Dict[str, int]]


class Syncer:
    def __init__(self) -> None:
        """
        size = source file size
        same = size of between two file same blocks
        diff = size of between two file diff blocks
        done = computed blocks
        delta = number of blocks lately changed
        last = recent block location
        """
        self.blocks: BlocksType = defaultdict(
            lambda: {"size": 0, "same": 0, "diff": 0, "done": 0, "delta": 0, "last": 0}
        )
        self.logger = logger
        self._sftp: Union[None, paramiko.SFTPClient] = None

    def fadvise(self, fd: IO, offset: int, length: int, advice: FADV) -> None:
        """
        POSIX fadvice

        POSIX_FADV_NOREUSE
        - tells the kernel that the file can be removed from cache,
          flag that gets invalidated if another process is accessing the same file

        POSIX_FADV_DONTNEED
        - removes the file from cache, whether the user is using the file or not
        """
        os.posix_fadvise(fd.fileno(), offset, length, advice.value)

    def do_create(self, path: str, size: int) -> None:
        """
        create file on local

        :param path: file path
        :param size: file size
        """
        with open(path, "a", os.SEEK_SET) as f:
            f.truncate(size)

    def do_open(self, path_: str, mode: str) -> Tuple[IO, int]:
        """
        open local file

        :param path_: file path
        :param mode: file open mode
        :return: file-object, file size
        """
        if __sftp_client := getattr(self, "_sftp_client", False):
            f = __sftp_client.file(filename=path_, mode=mode)
        else:
            f = open(path_, mode)
        f.seek(os.SEEK_SET, os.SEEK_END)
        size = f.tell()
        f.seek(os.SEEK_SET)
        return f, size

    def get_blocks(self, f: IO, block_size: int) -> Any:
        """
        read a block sequentially from the file

        :param f:
        :param block_size:
        :return:
        """
        while block := f.read(block_size):
            yield block

    def get_rate(self, dest: str) -> Union[float, None]:
        """
        :return: current sync rate
        """
        if dest in self.blocks:
            return (self.blocks[dest]["done"] / self.blocks[dest]["size"]) * 100

    def stop(self) -> None:
        """
        stop sync
        :return:
        """
        raise StopSync()

    def open_sftp(
        self,
        hostname: str,
        username: str = None,
        password: str = None,
        compress: bool = True,
        cipher: Tuple[str] = ("blowfish",),
        port: int = SSH_PORT,
        key_filename: str = None,
    ):
        with paramiko.SSHClient() as ssh:
            ssh.load_system_host_keys(key_filename)
            cipher = (
                c for c in paramiko.Transport._preferred_ciphers if c not in cipher
            )
            ssh.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                compress=compress,
                disabled_algorithms={"cipher": cipher},
            )
            self._sftp = ssh.open_sftp()

    def get_sftp_client(self) -> Union[None, paramiko.SFTPClient]:
        return self._sftp

    def serial_sync(
        self,
        src_dev: str,
        destinations: List[str],
        block_size: int = UNITS["MiB"],
        interval: int = 1,
        before: Callable = None,
        monitor: Callable = None,
        after: Callable = None,
        on_error: Callable = None,
        *args,
        **kwargs,
    ) -> None:
        if src_dev in destinations:
            raise ValueError("source and some destination same")

        src_dev, src_size = self.do_open(src_dev, "rb+")

        try:
            for dest in destinations:
                if callable(before):
                    before(*args, **kwargs)

                self._sync(
                    src_dev,
                    src_size,
                    dest,
                    block_size,
                    interval,
                    before,
                    monitor,
                    after,
                    on_error,
                    *args,
                    **kwargs,
                )

                if callable(after):
                    after(*args, **kwargs)
        except StopSync:
            self.logger.info("Force stop sync")
        except Exception as e:
            self.logger.error(e)

            if callable(on_error):
                on_error(*args, **kwargs)
        finally:
            src_dev.close()

    def _sync(
        self,
        src_dev: IO,
        src_size: int,
        dest: str,
        block_size: int,
        interval: int = 1,
        monitor: Callable = None,
        *args,
        **kwargs,
    ):
        dest_dev, dest_size = self.do_open(dest, "rb+")

        try:
            if src_size != dest_size:
                raise ValueError("size not same")

            self.logger.info(f"Start sync {dest_dev}")
            self.blocks[dest]["size"] = src_size
            t_last = 0

            for idx, block in enumerate(
                zip(
                    self.get_blocks(src_dev, block_size),
                    self.get_blocks(dest_dev, block_size),
                )
            ):
                if block[0] == block[1]:
                    self.blocks[dest]["same"] += 1
                else:
                    dest_dev.seek(-block_size, os.SEEK_CUR)
                    dest_dev.write(block[0])
                    self.blocks["diff"] += 1

                self.blocks[dest]["done"] = (
                    self.blocks[dest]["same"] + self.blocks[dest]["diff"]
                )

                t1 = time.time()
                if t1 - t_last >= interval:
                    self.blocks[dest]["delta"] = (
                        self.blocks[dest]["done"] - self.blocks[dest]["last"]
                    )
                    self.blocks[dest]["last"] = self.blocks[dest]["done"]

                    if monitor:
                        monitor(*args, **kwargs)

                    t_last = t1

                if (
                    self.blocks[dest]["same"] + self.blocks[dest]["diff"]
                ) == self.blocks[dest]["size"]:
                    break
        finally:
            dest_dev.close()
