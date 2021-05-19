import hashlib
import io
import logging
import threading
import time
import timeit
from math import ceil
from typing import IO, Any, Callable, Dict, Generator, Optional, Tuple, Union

import paramiko

from blocksync._consts import BASE_DIR, DIFF, SKIP, ByteSizes
from blocksync._hooks import Hooks
from blocksync._status import Status
from blocksync._sync_manager import SyncManager

__all__ = ["local_to_local", "local_to_remote", "remote_to_local"]

READ_SERVER_SCRIPT_NAME = "_read_server.py"
DEFAULT_READ_SERVER_SCRIPT_PATH = str((BASE_DIR / READ_SERVER_SCRIPT_NAME).resolve())
WRITE_SERVER_SCRIPT_NAME = "_write_server.py"
DEFAULT_WRITE_SERVER_SCRIPT_PATH = str((BASE_DIR / WRITE_SERVER_SCRIPT_NAME).resolve())

logger = logging.getLogger("blocksync")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def _get_block_size(block_size: Union[int, str]) -> int:
    if isinstance(block_size, str):
        return ByteSizes.parse_readable_byte_size(block_size)
    return block_size


def _get_range(worker_id: int, status: Status) -> Tuple[int, int]:
    start = status.chunk_size * (worker_id - 1)
    chunk_size = status.chunk_size
    if worker_id == status.workers:
        chunk_size += status.src_size % status.workers
    return start, ceil(chunk_size / status.block_size)


def _get_size(path: str) -> int:
    fileobj = open(path, "r")
    fileobj.seek(io.SEEK_SET, io.SEEK_END)
    size: int = fileobj.tell()
    fileobj.seek(io.SEEK_SET)
    return size


def _get_remotedev_size(ssh: paramiko.SSHClient, command: str, path: str) -> int:
    stdin, stdout, _ = ssh.exec_command(command)
    try:
        stdin.write(f"{path}\n")
        return int(stdout.readline())
    finally:
        stdout.close()
        stdin.close()


def _do_create(path: str, size: int):
    with open(path, "a+") as fileobj:
        fileobj.truncate(size)


def _get_blocks(fileobj: IO, block_size: int) -> Generator[bytes, None, None]:
    while block := fileobj.read(block_size):
        yield block


def _log(worker_id: int, msg: str, level: int = logging.INFO, *args, **kwargs):
    logger.log(level, f"[Worker {worker_id}]: {msg}", *args, **kwargs)


def _connect_ssh(
    allow_load_system_host_keys: bool = True,
    compress: bool = True,
    **ssh_config,
) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    if allow_load_system_host_keys:
        ssh.load_system_host_keys()
    ssh.connect(**ssh_config, compress=compress)
    return ssh


def _sync(
    manager: SyncManager,
    status: Status,
    workers: int,
    sync: Callable,
    sync_options: Dict[str, Any],
    wait: bool = False,
) -> Tuple[Optional[SyncManager], Status]:
    for i in range(1, workers + 1):
        sync_options["worker_id"] = i
        worker = threading.Thread(target=sync, kwargs=sync_options)
        worker.start()
        manager.workers.append(worker)
    if wait:
        manager.wait_sync()
        return None, status
    return manager, status


def local_to_local(
    src: str,
    dest: str,
    block_size: Union[str, int] = ByteSizes.MiB,
    workers: int = 1,
    create_dest: bool = False,
    wait: bool = False,
    dryrun: bool = False,
    on_before: Optional[Callable[..., Any]] = None,
    on_after: Optional[Callable[[Status], Any]] = None,
    monitor: Optional[Callable[[Status], Any]] = None,
    on_error: Optional[Callable[[Exception, Status], Any]] = None,
    monitoring_interval: Union[int, float] = 1,
    sync_interval: Union[int, float] = 0,
) -> Tuple[Optional[SyncManager], Status]:
    status = Status(
        workers=workers,
        block_size=_get_block_size(block_size),
        src_size=_get_size(src),
    )
    if create_dest:
        _do_create(dest, status.src_size)
    status.dest_size = _get_size(dest)
    manager = SyncManager()
    sync_options = {
        "src": src,
        "dest": dest,
        "status": status,
        "manager": manager,
        "hooks": Hooks(on_before=on_before, on_after=on_after, monitor=monitor, on_error=on_error),
        "dryrun": dryrun,
        "monitoring_interval": monitoring_interval,
        "sync_interval": sync_interval,
    }
    return _sync(manager, status, workers, _local_to_local, sync_options, wait)


def _local_to_local(
    worker_id: int,
    src: str,
    dest: str,
    status: Status,
    manager: SyncManager,
    hooks: Hooks,
    dryrun: bool,
    monitoring_interval: Union[int, float],
    sync_interval: Union[int, float],
):
    hooks.run_before()

    startpos, maxblock = _get_range(worker_id, status)
    _log(worker_id, f"Start sync({src} -> {dest}) {maxblock} blocks")
    srcdev = io.open(src, "rb+")
    destdev = io.open(dest, "rb+")
    srcdev.seek(startpos)
    destdev.seek(startpos)

    t_last = timeit.default_timer()
    try:
        for src_block, dest_block, _ in zip(
            _get_blocks(srcdev, status.block_size),
            _get_blocks(destdev, status.block_size),
            range(maxblock),
        ):
            if manager.suspended:
                _log(worker_id, "Waiting for resume...")
                manager._wait_resuming()
            if manager.canceled:
                break

            if src_block != dest_block:
                if not dryrun:
                    destdev.seek(-len(src_block), io.SEEK_CUR)
                    srcdev.write(src_block)
                    destdev.flush()
                status.add_block("diff")
            else:
                status.add_block("same")

            t_cur = timeit.default_timer()
            if monitoring_interval <= t_cur - t_last:
                hooks.run_monitor(status)
                t_last = t_cur
            if 0 < sync_interval:
                time.sleep(sync_interval)
    except Exception as e:
        _log(worker_id, msg=str(e), exc_info=True)
        hooks.run_on_error(e, status)
    finally:
        srcdev.close()
        destdev.close()
    hooks.run_after(status)


def local_to_remote(
    src: str,
    dest: str,
    block_size: Union[str, int] = ByteSizes.MiB,
    workers: int = 1,
    create_dest: bool = False,
    wait: bool = False,
    dryrun: bool = False,
    on_before: Optional[Callable[..., Any]] = None,
    on_after: Optional[Callable[[Status], Any]] = None,
    monitor: Optional[Callable[[Status], Any]] = None,
    on_error: Optional[Callable[[Exception, Status], Any]] = None,
    monitoring_interval: Union[int, float] = 1,
    sync_interval: Union[int, float] = 0,
    hash1: str = "sha256",
    read_server_command: Optional[str] = None,
    write_server_command: Optional[str] = None,
    allow_load_system_host_keys: bool = True,
    compress: bool = True,
    **ssh_config,
) -> Tuple[Optional[SyncManager], Status]:
    status: Status = Status(
        workers=workers,
        block_size=_get_block_size(block_size),
        src_size=_get_size(src),
    )

    ssh = _connect_ssh(allow_load_system_host_keys, compress, **ssh_config)
    if sftp := ssh.open_sftp():
        if read_server_command is None:
            sftp.put(DEFAULT_READ_SERVER_SCRIPT_PATH, READ_SERVER_SCRIPT_NAME)
            read_server_command = f"python3 {READ_SERVER_SCRIPT_NAME}"
        if write_server_command is None:
            sftp.put(DEFAULT_WRITE_SERVER_SCRIPT_PATH, WRITE_SERVER_SCRIPT_NAME)
            write_server_command = f"python3 {WRITE_SERVER_SCRIPT_NAME}"

    manager = SyncManager()
    sync_options = {
        "ssh": ssh,
        "src": src,
        "dest": dest,
        "status": status,
        "manager": manager,
        "create_dest": create_dest,
        "dryrun": dryrun,
        "hooks": Hooks(on_before=on_before, on_after=on_after, monitor=monitor, on_error=on_error),
        "monitoring_interval": monitoring_interval,
        "sync_interval": sync_interval,
        "hash1": hash1,
        "read_server_command": read_server_command,
        "write_server_command": write_server_command,
    }
    return _sync(manager, status, workers, _local_to_remote, sync_options, wait)


def _local_to_remote(
    worker_id: int,
    ssh: paramiko.SSHClient,
    src: str,
    dest: str,
    status: Status,
    manager: SyncManager,
    create_dest: bool,
    dryrun: bool,
    hooks: Hooks,
    monitoring_interval: Union[int, float],
    sync_interval: Union[int, float],
    hash1: str,
    read_server_command: str,
    write_server_command: str,
):
    hash_ = getattr(hashlib, hash1)
    hash_len = hash_().digest_size

    hooks.run_before()

    reader_stdin, reader_stdout, _ = ssh.exec_command(read_server_command)
    writer_stdin, writer_stdout, _ = ssh.exec_command(write_server_command)
    writer_stdin.write(f"{dest}\n{status.src_size if create_dest else 0}\n")
    reader_stdin.write(f"{dest}\n")
    status.dest_size = int(reader_stdout.readline())
    startpos, maxblock = _get_range(worker_id, status)
    _log(worker_id, f"Start sync({src} -> {dest}) {maxblock} blocks")
    reader_stdin.write(f"{status.block_size}\n{hash1}\n{startpos}\n{maxblock}\n")
    writer_stdin.write(f"{status.block_size}\n{startpos}\n{maxblock}\n")

    t_last = timeit.default_timer()
    with open(src, "rb+") as fileobj:
        fileobj.seek(startpos)
        try:
            for src_block, _ in zip(_get_blocks(fileobj, status.block_size), range(maxblock)):
                if manager.suspended:
                    _log(worker_id, "Waiting for resume...")
                    manager._wait_resuming()
                if manager.canceled:
                    break

                src_block_hash: bytes = hash_(src_block).digest()
                dest_block_hash: bytes = reader_stdout.read(hash_len)
                reader_stdin.write(SKIP)
                if src_block_hash != dest_block_hash:
                    if not dryrun:
                        writer_stdin.write(DIFF)
                        writer_stdin.write(src_block)
                    else:
                        writer_stdin.write(SKIP)
                    status.add_block("diff")
                else:
                    status.add_block("same")

                t_cur = timeit.default_timer()
                if monitoring_interval <= t_cur - t_last:
                    hooks.run_monitor(status)
                    t_last = t_cur
                if 0 < sync_interval:
                    time.sleep(sync_interval)
        except Exception as e:
            _log(worker_id, msg=str(e), exc_info=True)
            hooks.run_on_error(e, status)
        finally:
            reader_stdin.close()
            reader_stdout.close()
            writer_stdin.close()
            writer_stdout.close()
        hooks.run_after(status)


def remote_to_local(
    src: str,
    dest: str,
    block_size: Union[str, int] = ByteSizes.MiB,
    workers: int = 1,
    create_dest: bool = False,
    wait: bool = False,
    dryrun: bool = False,
    on_before: Optional[Callable[..., Any]] = None,
    on_after: Optional[Callable[[Status], Any]] = None,
    monitor: Optional[Callable[[Status], Any]] = None,
    on_error: Optional[Callable[[Exception, Status], Any]] = None,
    monitoring_interval: Union[int, float] = 1,
    sync_interval: Union[int, float] = 0,
    hash1: str = "sha256",
    allow_load_system_host_keys: bool = True,
    compress: bool = True,
    read_server_command: Optional[str] = None,
    **ssh_config,
):
    ssh = _connect_ssh(allow_load_system_host_keys, compress, **ssh_config)
    if read_server_command is None and (sftp := ssh.open_sftp()):
        sftp.put(DEFAULT_READ_SERVER_SCRIPT_PATH, READ_SERVER_SCRIPT_NAME)
        read_server_command = f"python3 {READ_SERVER_SCRIPT_NAME}"

    status = Status(
        workers=workers,
        block_size=ByteSizes.parse_readable_byte_size(block_size) if isinstance(block_size, str) else block_size,
        src_size=_get_remotedev_size(ssh, read_server_command, src),  # type: ignore[arg-type]
    )
    if create_dest:
        _do_create(dest, status.src_size)
    status.dest_size = _get_size(dest)
    manager = SyncManager()
    sync_options = {
        "ssh": ssh,
        "src": src,
        "dest": dest,
        "status": status,
        "manager": manager,
        "dryrun": dryrun,
        "hooks": Hooks(on_before=on_before, on_after=on_after, monitor=monitor, on_error=on_error),
        "monitoring_interval": monitoring_interval,
        "sync_interval": sync_interval,
        "hash1": hash1,
        "read_server_command": read_server_command,
    }
    return _sync(manager, status, workers, _remote_to_local, sync_options, wait)


def _remote_to_local(
    worker_id: int,
    ssh: paramiko.SSHClient,
    src: str,
    dest: str,
    status: Status,
    manager: SyncManager,
    dryrun: bool,
    monitoring_interval: Union[int, float],
    sync_interval: Union[int, float],
    hash1: str,
    read_server_command: str,
    hooks: Hooks,
):
    hash_ = getattr(hashlib, hash1)
    hash_len = hash_().digest_size

    hooks.run_before()

    reader_stdin, *_ = ssh.exec_command(read_server_command)
    reader_stdout = reader_stdin.channel.makefile("rb")
    reader_stdin.write(f"{src}\n")
    reader_stdout.readline()
    startpos, maxblock = _get_range(worker_id, status)
    _log(worker_id, f"Start sync({src} -> {dest}) {maxblock} blocks")
    reader_stdin.write(f"{status.block_size}\n{hash1}\n{startpos}\n{maxblock}\n")

    t_last = timeit.default_timer()
    with open(dest, "rb+") as fileobj:
        fileobj.seek(startpos)
        try:
            for dest_block, _ in zip(_get_blocks(fileobj, status.block_size), range(maxblock)):
                if manager.suspended:
                    _log(worker_id, "Waiting for resume...")
                    manager._wait_resuming()
                if manager.canceled:
                    break

                src_block_hash: bytes = reader_stdout.read(hash_len)
                dest_block_hash: bytes = hash_(dest_block).digest()
                if src_block_hash != dest_block_hash:
                    if not dryrun:
                        reader_stdin.write(DIFF)
                        src_block = reader_stdout.read(status.block_size)
                        fileobj.seek(-len(src_block), io.SEEK_CUR)
                        fileobj.write(src_block)
                        fileobj.flush()
                    else:
                        reader_stdin.write(SKIP)
                    status.add_block("diff")
                else:
                    reader_stdin.write(SKIP)
                    status.add_block("same")

                t_cur = timeit.default_timer()
                if monitoring_interval <= t_cur - t_last:
                    hooks.run_monitor(status)
                    t_last = t_cur
                if 0 < sync_interval:
                    time.sleep(sync_interval)
        except Exception as e:
            _log(worker_id, msg=str(e), exc_info=True)
            hooks.run_on_error(e, status)
        finally:
            reader_stdin.close()
            reader_stdout.close()
        hooks.run_after(status)
