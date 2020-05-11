import blocksync


source_file = blocksync.File("source.file")
destination_file = blocksync.File("destination.file")
syncer = blocksync.Syncer(source_file, destination_file)
syncer.start_sync()
