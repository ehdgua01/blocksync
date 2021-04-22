# blocksync

[![Build](https://travis-ci.com/ehdgua01/blocksync.svg?branch=master)](https://travis-ci.com/github/ehdgua01/blocksync)
[![Coverage](https://codecov.io/gh/ehdgua01/blocksync/branch/master/graph/badge.svg)](https://app.codecov.io/gh/ehdgua01/blocksync)
[![PyPi](https://badge.fury.io/py/blocksync.svg)](https://pypi.org/project/blocksync/)
[![PyVersions](https://img.shields.io/pypi/pyversions/blocksync)](https://pypi.org/project/blocksync/)

Blocksync Python package allows [blocksync script](https://github.com/theraser/blocksync) to be used as Python packages,
and supports more convenient and various functions than blocksync script.

# Prerequisites

- Python 3.8 or later

# Features

- Synchronize the destination (remote or local) files using an incremental algorithm.
- Supports all synchronization directions. (local-local, local-remote, remote-local, remote-remote)
- Support for callbacks that can run before(run once or per workers), after(run once or per workers), and during synchronization of files
- Support for synchronization suspend/resume, cancel.
- Most methods support method chaining.
- You can see the overall progress in a multi-threaded environment.
- You can proceed synchronization in the background.
- You can specify the number of workers (number of threads) to perform synchronization.

# Installation

```bash
pip install blocksync
```

# Quick start

When using SFTP files, you can check the SSH connection options in [paramiko docs](http://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient).

```python
from blocksync import LocalFile, SFTPFile, Syncer


syncer = Syncer(
    src=SFTPFile(
        path="src.file",
        hostname="hostname",
        username="username",
        password="password",
        key_filename="key_filepath",
    ),
    dest=LocalFile(path="dest.file"),
)
syncer.start_sync(workers=2, create=True, wait=True)
```


# TODO
- [ ] Provide CLI
- [ ] Write docs and build a docs website

# License
MIT License (For more information about this license, please see [this](https://en.wikipedia.org/wiki/MIT_License))
