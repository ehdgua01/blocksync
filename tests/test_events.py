from blocksync.events import Events


def test_initialize_events():
    # Expect: Set all event's flags to True
    events = Events()
    events.suspended.clear()
    events.canceled.clear()
    events.initialize()
    assert events.suspended.is_set()
    assert events.canceled.is_set()
