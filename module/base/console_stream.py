"""Keep a detached launcher console from terminating backend workers."""
import os
import sys


class DetachedConsoleStream:
    def __init__(self, stream):
        self._stream = stream

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def _detach(self):
        # Do not close the inherited handle: other libraries may still own it.
        # File logging and the worker's live log pipe are separate channels.
        self._stream = open(os.devnull, 'w', encoding='utf-8')

    def write(self, text):
        try:
            return self._stream.write(text)
        except (OSError, ValueError):
            self._detach()
            return len(text)

    def flush(self):
        try:
            self._stream.flush()
        except (OSError, ValueError):
            self._detach()

    def isatty(self):
        try:
            return self._stream.isatty()
        except (OSError, ValueError):
            self._detach()
            return False

    def fileno(self):
        try:
            return self._stream.fileno()
        except (OSError, ValueError):
            self._detach()
            return self._stream.fileno()


def protect_console_streams():
    for name in ('stdout', 'stderr'):
        stream = getattr(sys, name)
        if stream is not None and not isinstance(stream, DetachedConsoleStream):
            setattr(sys, name, DetachedConsoleStream(stream))
