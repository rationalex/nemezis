import time


def now():
    return time.time()


class Timer:
    def __enter__(self):
        self.start = now()
        return self

    def __exit__(self, *args):
        self.end = now()
        self.interval = self.end - self.start
