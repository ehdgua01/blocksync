import threading

__all__ = ["Events"]


class Events:
    def __init__(self):
        self.prepared: threading.Event = threading.Event()
        self.suspended: threading.Event = threading.Event()
        self.canceled: threading.Event = threading.Event()

    def initialize(self):
        self.prepared.set()
        self.suspended.set()
        self.canceled.set()
