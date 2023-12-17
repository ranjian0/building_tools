from functools import wraps


class Events:
    def __init__(self, events):
        self.subscribers = {e: list() for e in events}

    def get_subscribers(self, event):
        return self.subscribers.get(event, None)

    def on(self, event):
        def wrapper(callback):
            self.get_subscribers(event).append(callback)

        return wrapper

    def register(self, event, callback):
        self.get_subscribers(event).append(callback)

    def register_all(self, callback):
        for event in self.subscribers.keys():
            self.subscribers[event].append(callback)

    def unregister(self, event, callback):
        self.get_subscribers(event).remove(callback)

    def dispatch(self, event, *args, **kwargs):
        for callback in self.get_subscribers(event):
            callback(*args, **kwargs)
