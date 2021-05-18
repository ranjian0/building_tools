from functools import wraps


class Events:

    def __init__(self, events):
        self.subscribers = {e:list() for e in events}

    def get_subscribers(self, event):
        return self.subscribers[event]

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

    def dispatch(self, event, message):
        for callback in self.get_subscribers(event):
            callback(message)


if __name__ == "__main__":
    Events = Publisher([
        "size_changed",
        "offset_changed",
        "array_count_changed",
        "array_spread_changed"
    ])


    @Events.on("size_changed")
    def sch(v):
        print("received .. ", v)


    class Dog:
        def foo(self, w):
            print("Dog received", w)

    d = Dog()
    Events.register("size_changed", d.foo)

    Events.dispatch("size_changed", 10)
