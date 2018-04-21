import time
import random
from contextlib import contextmanager
from multiprocessing import Lock, BoundedSemaphore, Value


class RequestManager:
    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.lock = Lock()
        self.sem = BoundedSemaphore(max_workers)
        self.last_request = Value('d', 0.0)
        self.last_restricted_request = Value('d', 0.0)

    @contextmanager
    def normal_request(self):
        with self.lock:
            self.sem.acquire()
        time.sleep(max(0.0, self.last_restricted_request.value + 0.6 + (random.random() * 0.15) - time.time()))
        yield None
        self.last_request.value = time.time()
        self.sem.release()

    @contextmanager
    def restricted_request(self):
        with self.lock:
            for i in range(self.max_workers):
                self.sem.acquire()
        time.sleep(max(0.0, self.last_request.value + 0.6 + (random.random() * 0.15) - time.time()))
        yield None
        self.last_request.value = time.time()
        self.last_restricted_request.value = time.time()
        for i in range(self.max_workers):
            self.sem.release()
