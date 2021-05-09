# blocksync

Blocksync Python package allows [blocksync script](https://github.com/theraser/blocksync) to be used as Python packages,
and supports more convenient and various functions than blocksync script.

[![Build](https://img.shields.io/travis/ehdgua01/blocksync/master.svg?style=for-the-badge&logo=travis)](https://travis-ci.com/github/ehdgua01/blocksync)
[![Coverage](https://img.shields.io/codecov/c/github/ehdgua01/blocksync?logo=codecov&style=for-the-badge)](https://app.codecov.io/gh/ehdgua01/blocksync)
[![PyPi](https://img.shields.io/pypi/v/blocksync?logo=pypi&style=for-the-badge)](https://pypi.org/project/blocksync/)
[![PyVersions](https://img.shields.io/pypi/pyversions/blocksync?logo=python&style=for-the-badge)](https://pypi.org/project/blocksync/)

# Prerequisites

- Python 3.8 or later

# Features

- Synchronize the destination (remote or local) files using an incremental algorithm.
- Supports all synchronization directions. (local-local, local-remote, remote-local)
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

When sync from/to remote, you can check the SSH connection options in [paramiko docs](http://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient).

```python
from blocksync import local_to_local

manager, status = local_to_local("src.txt", "dest.txt", workers=4)
manager.wait_sync()
print(status)

# Output
{'workers': 1, 'chunk_size': 251, 'block_size': 1048576, 'src_size': 1007, 'dest_size': 1007, 'blocks': {'same': 4, 'diff': 0, 'done': 4}}
```


# TODO
- [ ] Provide CLI
- [ ] Write docs and build a docs website

# License
MIT License (For more information about this license, please see [this](https://en.wikipedia.org/wiki/MIT_License))
