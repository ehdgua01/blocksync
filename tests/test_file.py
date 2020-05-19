import pathlib
import unittest
import paramiko

from blocksync import File


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
        __local_file = pathlib.Path("local.file")
        __local_file.unlink(missing_ok=True)

        if self.remote_file.connected:
            self.remote_file._local.sftp.remove(self._remote_path)

    def test_open_sftp_and_close_sftp(self) -> None:
        self.assertEqual(self.remote_file.connected, False)
        self.assertEqual(self.remote_file.open_sftp(), self.remote_file)
        self.assertTrue(isinstance(self.remote_file._local.ssh, paramiko.SSHClient))
        self.assertEqual(self.remote_file.connected, True)

        self.assertEqual(self.remote_file.close_sftp(), self.remote_file)
        self.assertEqual(self.remote_file.connected, False)

    def test_create_a_1MB_local_file(self) -> None:
        self.assertEqual(self.local_file.do_create(1000), self.local_file)
        __local_file = pathlib.Path("local.file")
        self.assertEqual(__local_file.stat().st_size, 1000)

    def test_create_a_1MB_remote_file(self) -> None:
        self.assertEqual(self.remote_file.do_create(1000), self.remote_file)

        if self.remote_file.connected:
            self.assertEqual(
                self.remote_file._local.sftp.stat(self._remote_path).st_size, 1000
            )

    def test_open_local_file(self) -> None:
        self.local_file.do_create()
        self.assertEqual(self.local_file.opened, False)
        self.assertEqual(self.local_file.do_open(), self.local_file)
        self.assertEqual(self.local_file.opened, True)

    def test_open_remote_file(self) -> None:
        self.remote_file.do_create()
        self.assertEqual(self.remote_file.opened, False)
        self.assertEqual(self.remote_file.do_open(), self.remote_file)
        self.assertEqual(self.remote_file.opened, True)

    def test_invalid_ssh_cipher(self) -> None:
        with self.assertRaises(ValueError):
            File("test_file", remote=True, cipher="invalid_cipher")
