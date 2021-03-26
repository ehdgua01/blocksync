import blocksync

source_file = blocksync.File("source.file")
source_file.do_create(10_000)
destination_file = blocksync.File(
    "destination.file",
    remote=True,
    hostname="192.168.0.3",
    username="example_user",
    password="example_password",
    compress=True,
)
syncer = blocksync.Syncer(source_file, destination_file)
syncer.start_sync(create=True)
