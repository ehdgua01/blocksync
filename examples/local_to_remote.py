import blocksync


source_file = blocksync.File("source.file")
destination_file = blocksync.File(
    "destination.file",
    remote=True,
    hostname="192.168.0.3",
    username="example_user",
    password="example_password",
    compress=True,
    port=22,
    key_filename="",
    cipher="aes128-ctr"
)
syncer = blocksync.Syncer(source_file, destination_file)
syncer.start_sync()
