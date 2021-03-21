import blocksync


source_file = blocksync.File("source.file")
destination_file = blocksync.File("destination.file")
syncer = blocksync.Syncer()
syncer.set_source(source_file)
syncer.set_destination(destination_file)
syncer.start_sync()
