"""Best-effort live log delivery; file logging remains independent and complete."""
from queue import Empty, Full, Queue
from threading import Event, Thread


class BufferedLogSender:
    def __init__(self, send, capacity=256):
        self.send = send
        self.queue = Queue(maxsize=capacity)
        self.closed = Event()
        self.thread = Thread(target=self._run, name='worker-live-log', daemon=True)
        self.thread.start()

    def __call__(self, message):
        if self.closed.is_set():
            return
        try:
            self.queue.put_nowait(message)
        except Full:
            # Retain recent live output without ever waiting for the pipe.
            try:
                self.queue.get_nowait()
            except Empty:
                pass
            try:
                self.queue.put_nowait(message)
            except Full:
                pass

    def _run(self):
        while True:
            try:
                message = self.queue.get(timeout=0.1)
            except Empty:
                if self.closed.is_set():
                    return
                continue
            try:
                self.send(message)
            except Exception:
                # A broken monitoring pipe must not abort the game task.
                self.closed.set()
                return

    def close(self, timeout=0.5):
        self.closed.set()
        self.thread.join(timeout)
