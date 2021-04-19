import threading

__all__ = ["Events"]


class Events:
    def __init__(self):
        self.suspended: threading.Event = threading.Event()
        self.canceled: threading.Event = threading.Event()

    def initialize(self):
        self.suspended.set()
        self.canceled.set()
