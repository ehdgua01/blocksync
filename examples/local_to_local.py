import blocksync

size = 10_000
source_file = blocksync.File("source.file")
source_file.do_create(size)
destination_file = blocksync.File("destination.file")
syncer = blocksync.Syncer(source_file, destination_file)
syncer.start_sync(create=True)
