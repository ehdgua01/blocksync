import blocksync

source_file = blocksync.File("source.file").do_create(10_000)
destination_file = blocksync.File("destination.file")
syncer = blocksync.Syncer(source_file, destination_file)
syncer.start_sync(create=True)
