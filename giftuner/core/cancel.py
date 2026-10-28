"""Cooperative cancellation for the external-binary pipeline.

RIFE / Real-ESRGAN run as blocking child processes, so a plain flag can't
interrupt them. A ``CancelToken`` both flags cancellation *and* keeps a
handle to the running subprocess so it can be killed immediately.
"""
from __future__ import annotations

import threading


class ProcessCancelled(Exception):
    """Raised inside the worker pipeline when the user cancels."""


class CancelToken:
    def __init__(self) -> None:
        self._cancelled = False
        self._proc = None  # subprocess.Popen | None
        self._lock = threading.Lock()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Flag cancellation and kill any currently-running subprocess.

        Safe to call from another thread (the UI thread)."""
        with self._lock:
            self._cancelled = True
            proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    def attach(self, proc) -> None:
        """Register the running subprocess. If cancellation already
        happened, kill it right away."""
        with self._lock:
            self._proc = proc
            already = self._cancelled
        if already and proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    def detach(self) -> None:
        with self._lock:
            self._proc = None

    def raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise ProcessCancelled()
