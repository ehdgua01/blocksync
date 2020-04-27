import os
import time
from typing import Callable, List, Tuple
import paramiko

from blocksync.syncer import Syncer
from blocksync.consts import UNITS, SSH_PORT
from blocksync.exception import StopSync, ForceStopSync


class RemoteSyncer(Syncer):
    def __init__(
        self,
        hostname: str,
        username: str = None,
        password: str = None,
        compress: bool = True,
        cipher: Tuple[str] = ("blowfish",),
        port: int = SSH_PORT,
        key_filename: str = None,
    ):
        super().__init__()
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
                disabled_algorithms={"cipher": cipher,},
            )
            self._sftp_client = ssh.open_sftp()

    def sync(
        self,
        src_dev: str,
        dest_dev: List[str],
        block_size: int = UNITS["MiB"],
        interval: int = 1,
        before: Callable = None,
        monitor: Callable = None,
        after: Callable = None,
        on_error: Callable = None,
        *args,
        **kwargs,
    ) -> None:
        if src_dev in dest_dev:
            raise ValueError("source and destination are same")

        src_dev, src_size = self.do_open(src_dev, "rb+")

        if before:
            before(*args, **kwargs)

        try:
            for dest in dest_dev:
                self.logger.info(f"Start sync {dest}")
                __dev, __size = self.do_open(dest, "rb+", True)

                if src_size != __size:
                    raise ValueError("size not same")

                try:
                    self.blocks["size"] = src_size
                    t_last = 0

                    for idx, block in enumerate(
                        zip(
                            self.get_blocks(src_dev, block_size),
                            self.get_blocks(__dev, block_size),
                        )
                    ):
                        if block[0] == block[1]:
                            self.blocks["same"] += 1
                        else:
                            __dev.seek(-block_size, os.SEEK_CUR)
                            __dev.write(block[0])
                            self.blocks["diff"] += 1

                        self.blocks["done"] = self.blocks["same"] + self.blocks["diff"]

                        t1 = time.time()
                        if t1 - t_last >= interval:
                            self.blocks["delta"] = (
                                self.blocks["done"] - self.blocks["last"]
                            )
                            self.blocks["last"] = self.blocks["done"]

                            if monitor:
                                monitor(*args, **kwargs)

                            t_last = t1

                        if (self.blocks["same"] + self.blocks["diff"]) == self.blocks[
                            "size"
                        ]:
                            break

                    if after:
                        after(*args, **kwargs)
                finally:
                    __dev.close()
        except ForceStopSync:
            self.logger.info("Force stop sync")
        except (Exception, StopSync) as e:
            self.logger.error(e)
            on_error(*args, **kwargs)
        finally:
            src_dev.close()
