blocksync
=========

Blocksync Python package allows `blocksync script`_ to be used as Python packages,
and supports more convenient and various functions than blocksync script.

.. _blocksync script: https://github.com/theraser/blocksync

.. image:: https://travis-ci.com/ehdgua01/blocksync.svg?branch=master
    :target: https://travis-ci.com/ehdgua01/blocksync

.. image:: https://codecov.io/gh/ehdgua01/blocksync/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/ehdgua01/blocksync

.. image:: https://badge.fury.io/py/blocksync.svg
    :target: https://badge.fury.io/py/blocksync

Prerequisites
-------------
* Python 3.8 or later

Installation
------------
.. code-block:: bash

    pip install blocksync

Features
--------
* Synchronize the destination (remote or local) files using an incremental algorithm.
* Supports all direction of synchronization. (local-local, local-remote, remote-local, remote-remote)
* Support for callbacks that can run before, after, and during synchronization of files
* Support for synchronization suspend/resume, cancel.
* Most methods support method chaining.
* You can see the overall progress in a multi-threaded environment.
* You can proceed synchronization in the background.
* You can multi hash when comparing data. (you can use all hash algorithm supported by `hashlib`_)
* You can specify the number of workers (number of threads) to perform synchronization.

.. _hashlib: https://docs.python.org/3/library/hashlib.html

Notes
-------------
- You can sync with only one worker when you sync `block device(or special device)`_
  because Python cannot get the size of the block device before reading it. See `description`_

.. _block device(or special device): https://en.wikipedia.org/wiki/Device_file
.. _description: https://docs.python.org/3/library/stat.html#stat.ST_CTIME

License
-------
MIT License (For more information about this license, please see `this`_)

.. _this: https://en.wikipedia.org/wiki/MIT_License
