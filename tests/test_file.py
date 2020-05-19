import unittest
import paramiko

from blocksync import File


class TestCase(unittest.TestCase):
    _server_addr = "localhost"

    def setUp(self) -> None:
        self.local_file = File("local.file")
        self.remote_file = File("remote.file", remote=True, hostname=self._server_addr)

    def test_remote_connection(self):
        self.assertEqual(self.remote_file.connected, False)
        self.assertEqual(self.remote_file.open_sftp(), self.remote_file)
        self.assertTrue(isinstance(self.remote_file._local.ssh, paramiko.SSHClient))
        self.assertEqual(self.remote_file.connected, True)

    def test_invalid_ssh_cipher(self):
        with self.assertRaises(ValueError):
            File("test_file", remote=True, cipher="invalid_cipher")
