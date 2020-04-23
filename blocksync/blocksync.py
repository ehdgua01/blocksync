import socket
import time
import os
import requests
import logging

logger = logging.getLogger(__name__)


class BlockSync(object):
    """동기화가 필요한 두 파일간의 diff만을 동기화"""

    SAME = b"0"
    DIFF = b"1"
    COMPLEN = len(SAME)
    MiB = 1024 * 1024
    BUFFER_SIZE = 4096

    def __init__(self):
        self.socket_: socket = None

    @staticmethod
    def fadvise(file_obj, offset, length, advice):
        """
        POSIX_FADV_NOREUSE
        - tells the kernel that the file can be removed from cache,
          flag that gets invalidated if another process is accessing the same file

        POSIX_FADV_DONTNEED
        - removes the file from cache, whether the user is using the file or not
        """
        return os.posix_fadvise(file_obj.fileno(), offset, length, advice)

    @staticmethod
    def do_create(path: str, size: int):
        """
        :param path: file path
        :param size: file size
        """
        with open(path, "a", os.SEEK_SET) as f:
            f.truncate(size)

    def do_open(self, f: str, mode: str) -> tuple:
        """
        :param f: file path
        :param mode: file open mode
        :return: file-object, file size
        """
        f = open(f, mode)
        self.fadvise(f, 0, 0, os.POSIX_FADV_NOREUSE)

        f.seek(os.SEEK_SET, os.SEEK_END)
        size = f.tell()
        f.seek(os.SEEK_SET)
        return f, size

    def get_blocks(self, f, block_size):
        while True:
            block = f.read(block_size)

            if not block:
                break

            """읽어 들인 크기만큼 cache 제거
            """
            self.fadvise(
                f, f.tell() - block_size, block_size, os.POSIX_FADV_DONTNEED,
            )
            yield block

    @staticmethod
    def get_rate(size_blocks, done_blocks) -> int:
        """
        현재 작업 진행율

        :param size_blocks: 전체 block 크기
        :param done_blocks: 작업이 완료된 block 수
        :return: float
        """
        return int(round((done_blocks / size_blocks) * 100, 0))

    @staticmethod
    def get_speed(t1, t2, block_size, unit=MiB) -> float:
        """
        현재 작업 진행 속도

        :param t1: 이전 시간
        :param t2: 현재 시간
        :param block_size: t1 t2 사이에 발생된 입출력 데이터 크기
        :param unit: block unit
        :return: float
        """
        if t2 > t1:
            temp = t1
            t1 = t2
            t2 = temp
        return round(block_size / ((t1 - t2) * unit), 2)

    def recv_all(self, buffer_size=BUFFER_SIZE):
        if self.socket_ is None:
            raise Exception("socket is none")

        data = b""

        while True:
            packet = self.socket_.recv(buffer_size)
            data += packet

            if packet < buffer_size:
                return data

    def new_sync_channel(self, addr_family, port=None, wait_timeout=60):
        self.socket_ = socket.socket(addr_family, socket.SOCK_STREAM,)
        self.socket_.settimeout(wait_timeout)
        self.socket_.listen(1)
        self.socket_.bind(("0.0.0.0", port if port else 0))
        return self.socket_

    def start_sync_channel(self, socket_: socket = None):
        if socket_:
            self.socket_ = socket_

        self.socket_, addr = socket_.accept()
        dest = str(self.recv_all().strip())
        create = int(self.recv_all().strip())

        if create > 0:
            self.do_create(dest, create)

        dest_dev, dest_size = self.do_open(dest, "rb+")
        """수신 서버의 파일 크기 전달하여 같은 크기의 파일인지 검사
        송신 서버에서 크기가 다를 시 socket 닫음
        """
        self.socket_.sendall(str(dest_size).encode())
        block_size = int(self.recv_all())

        for block in self.get_blocks(dest_dev, block_size):
            self.socket_.sendall(block)
            res = self.socket_.recv(self.COMPLEN)

            if res == self.DIFF:
                new_block = self.socket_.recv(block_size)
                dest_dev.seek(-block_size)
                dest_dev.write(new_block)

    def sync(self, server: str, src_dev: str, dest_dev: str, **kwargs):
        """
        size_blocks = 원본 파일 크기
        same_blocks = 두 파일간의 같은 block 수
        diff_blocks = 두 파일간의 다른 block 수
        done_blocks = 작업이 완료된 block 수
        delta_block = 마지막 작업 block 위치와의 변화량
        last_block = 마지막 작업 block 위치
        before: 동기화 전 실행될 callback 함수
        after: 동기화 완료 이후 실행될 callback 함수
        on_error: 에러 발생 시 실행 시킬 callback 함수
        """
        blocks = {
            "size_blocks": 0,
            "same_blocks": 0,
            "diff_blocks": 0,
            "done_blocks": 0,
            "delta_block": 0,
            "last_block": 0,
            "rate": -1,
        }
        before = kwargs.get("before")
        after = kwargs.get("after")
        on_error = kwargs.get("on_error")

        if before:
            before()

        try:
            if server == "localhost":
                if src_dev == dest_dev:
                    raise ValueError("Error same source and destination")

                src_dev, source_size = self.do_open(src_dev, "rb+")
                dest_dev, dest_size = self.do_open(dest_dev, "rb+")

                try:
                    if source_size != dest_size:
                        raise Exception("Error devices size not same")

                    blocks["size_blocks"] = source_size
                    return self.local_sync(src_dev, dest_dev, blocks, **kwargs)
                finally:
                    src_dev.close()
                    dest_dev.close()
            else:
                """
                url: receiver server's API

                example)
                response = requests.request(
                    method=kwargs.get('method', 'GET'),
                    url='http://192.168.0.5/sync',
                    # 다른 파라미터가 필요할 경우 kwargs로 전달하여 설정
                )

                # Response type => JSON
                response: {
                    socket_addr: socket address
                    port: socket port
                }
                """
                response = requests.request(
                    method=kwargs.get("method", "GET"), url=server, **kwargs,
                )

                if response.status_code != 200:
                    return

                response_json = response.json()
                return self.remote_sync(
                    src_dev=src_dev,
                    dest_dev=dest_dev,
                    address=response_json.get("socket_addr"),
                    port=response_json.get("port"),
                )
        except Exception as e:
            logger.error(e, exc_info=True)

            if on_error:
                on_error()

        finally:
            if after:
                after()

    def local_sync(
        self, src_dev, dest_dev, blocks: dict, block_size=MiB, interval=1, **kwargs
    ):
        """
        monitoring: interval마다 실행될 callback 함수
        """
        t0 = time.time()
        t_last = 0
        monitoring = kwargs.get("monitoring")

        for idx, block in enumerate(
            zip(
                self.get_blocks(src_dev, block_size),
                self.get_blocks(dest_dev, block_size),
            )
        ):
            if block[0] == block[1]:
                blocks["same_blocks"] += 1
            else:
                dest_dev.seek(-block_size, os.SEEK_CUR)
                dest_dev.write(block[0])
                blocks["diff_blocks"] += 1

            t1 = time.time()
            blocks["done_blocks"] = blocks["same_blocks"] + blocks["diff_blocks"]

            if t1 - t_last >= interval:
                blocks["delta_block"] = blocks["done_blocks"] - blocks["last_block"]
                blocks["last_block"] = blocks["done_blocks"]
                blocks["rate"] = self.get_rate(
                    size_blocks=blocks["size_blocks"],
                    done_blocks=blocks["done_blocks"] * block_size,
                )

                if monitoring:
                    monitoring(**blocks)

                t_last = t1

            if (blocks["same_blocks"] + blocks["diff_blocks"]) == blocks["size_blocks"]:
                break

        t_last = time.time()
        logger.debug(
            {
                "same": blocks["same_blocks"],
                "diff": blocks["diff_blocks"],
                "speed": self.get_speed(
                    t1=t0,
                    t2=t_last,
                    block_size=blocks["done_blocks"] * block_size,
                    unit=block_size,
                ),
                "elapsed": t_last - t0,
            }
        )
        return blocks

    def remote_sync(self, src_dev, dest_dev, address, port, **kwargs):
        # TODO: remote sync by socket
        pass
