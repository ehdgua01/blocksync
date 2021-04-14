import threading

__all__ = ["Events"]


class Events:
    def __init__(self):
        self.pre_event: threading.Event = threading.Event()
        self.suspend_event: threading.Event = threading.Event()
        self.canceled: bool = False

    def initialize(self):
        self.pre_event.clear()
        self.suspend_event.set()
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def suspend(self):
        self.suspend_event.clear()

    def resume(self):
        self.suspend_event.set()

    def wait(self):
        self.suspend_event.wait()

    @property
    def is_suspended(self):
        return not self.suspend_event.is_set()
