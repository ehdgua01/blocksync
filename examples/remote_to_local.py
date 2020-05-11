import blocksync


source_file = blocksync.File(
    "source.file",
    remote=True,
    hostname="192.168.0.2",
    username="example_user",
    password="example_password",
    compress=True,
    port=22,
    key_filename="",
    cipher="aes128-ctr"
)
destination_file = blocksync.File("destination.file")
syncer = blocksync.Syncer(source_file, destination_file)
syncer.start_sync()
