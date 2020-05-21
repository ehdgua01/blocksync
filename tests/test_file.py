import pathlib
import unittest
import paramiko

from blocksync import File
from blocksync.consts import UNITS
from blocksync.utils import generate_random_data


class TestCase(unittest.TestCase):
    _server_addr = "localhost"
    _local_path = "local.file"
    _remote_path = "remote.file"

    def setUp(self) -> None:
        self.local_file = File(self._local_path)
        self.remote_file = File(
            self._remote_path, remote=True, hostname=self._server_addr
        )

    def tearDown(self) -> None:
        pathlib.Path(self._local_path).unlink(missing_ok=True)

        if self.remote_file.connected:
            try:
                self.remote_file._local.sftp.remove(self._remote_path)
                self.remote_file.do_close(close_sftp=True)
            except:
                pass

    def test_open_sftp_and_close_sftp(self) -> None:
        self.assertFalse(self.remote_file.connected)
        self.assertFalse(getattr(self.remote_file._local, "ssh", False))

        self.assertEqual(self.remote_file.open_sftp(), self.remote_file)

        self.assertTrue(isinstance(self.remote_file._local.ssh, paramiko.SSHClient))
        self.assertTrue(self.remote_file.connected)

        # do close and close sftp
        self.assertEqual(self.remote_file.close_sftp(), self.remote_file)
        self.assertFalse(self.remote_file.connected)

    def test_create_a_1MiB_local_file(self) -> None:
        self.assertEqual(self.local_file.do_create(UNITS["MiB"]), self.local_file)

        __local_file = pathlib.Path("local.file")

        self.assertEqual(__local_file.stat().st_size, UNITS["MiB"])

    def test_create_a_1MiB_remote_file(self) -> None:
        self.assertEqual(self.remote_file.do_create(UNITS["MiB"]), self.remote_file)

        if self.remote_file.connected:
            self.assertEqual(
                self.remote_file._local.sftp.stat(self._remote_path).st_size,
                UNITS["MiB"],
            )

    def test_open_and_close_local_file(self) -> None:
        self.local_file.do_create()

        # open
        self.assertFalse(self.local_file.opened)
        self.assertEqual(self.local_file.do_open(), self.local_file)
        self.assertTrue(self.local_file.opened)

        # close
        self.assertEqual(self.local_file.do_close(), self.local_file)
        self.assertFalse(self.local_file.opened)
        self.assertFalse(self.local_file.connected)

    def test_open_and_close_remote_file(self) -> None:
        self.remote_file.do_create()

        # open
        self.assertFalse(self.remote_file.opened)
        self.assertEqual(self.remote_file.do_open(), self.remote_file)
        self.assertTrue(self.remote_file.opened)

        # close file and sftp connection
        self.assertEqual(self.remote_file.do_close(), self.remote_file)
        self.assertFalse(self.remote_file.opened)
        self.assertFalse(self.remote_file.connected)

        self.remote_file.do_open()

        # close only file
        self.assertEqual(self.remote_file.do_close(close_sftp=False), self.remote_file)
        self.assertFalse(self.remote_file.opened)
        self.assertTrue(self.remote_file.connected)

    def test_write_and_get_1MiB_blocks(self) -> None:
        write_data = generate_random_data(UNITS["MiB"]).encode()

        self.remote_file.do_create().do_open().execute("write", write_data).execute(
            "flush"
        ).execute("seek", 0)

        self.assertEqual(b"".join(self.remote_file.get_blocks()), write_data)

    def test_self_return_if_sftp_is_already_open(self) -> None:
        __ssh = self.remote_file.open_sftp()._local.ssh
        self.assertEqual(self.remote_file.open_sftp()._local.ssh, __ssh)

    def test_self_return_if_file_is_already_open(self) -> None:
        self.remote_file.do_create()
        __io = self.remote_file.do_open()._local.io
        self.assertEqual(self.remote_file.do_open()._local.io, __io)

    def test_should_be_fine_if_close_not_opened_file(self) -> None:
        self.assertEqual(self.local_file.do_close(), self.local_file)
        self.assertEqual(self.remote_file.do_close(), self.remote_file)

    def test_ssh_session_recyclable(self) -> None:
        __ssh = paramiko.SSHClient()

        with self.assertRaises(ValueError):
            # Only connected sessions are possible
            self.remote_file.open_sftp(session=__ssh)

        with self.assertRaises(ValueError):
            # session must be an instance of paramiko.SSHClient
            self.remote_file.open_sftp(session={})

        __ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        __ssh.load_system_host_keys()
        __ssh.connect(self._server_addr)
        self.remote_file.open_sftp(session=__ssh)
        self.assertEqual(self.remote_file._local.ssh, __ssh)

    def test_raise_error_when_execute_not_opened_file(self) -> None:
        with self.assertRaises(AttributeError):
            self.local_file.execute("seek", 0)

        with self.assertRaises(AttributeError):
            self.local_file.execute_with_result("seek", 0)

    def test_invalid_ssh_cipher(self) -> None:
        with self.assertRaises(ValueError):
            File("test_file", remote=True, cipher="invalid_cipher")
