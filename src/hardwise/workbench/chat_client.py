"""Share a model client across request snapshots, initializing only on AI use."""

from threading import RLock


class WorkbenchAIUnavailable(RuntimeError):
    """AI is unavailable; deterministic review remains independently usable."""


class DeferredWorkbenchClient:
    def __init__(self, factory):
        self._factory = factory
        self._client = None
        self._lock = RLock()

    @property
    def messages(self):
        with self._lock:
            if self._client is None:
                # Failed initialization is intentionally retryable. Shallow
                # service snapshots share this holder and the successful client.
                self._client = self._factory()
            return self._client.messages
