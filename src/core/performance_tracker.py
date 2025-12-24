"""Performance tracking for primitive execution"""

import time
from contextlib import contextmanager


class PerformanceTracker:
    """Tracks execution time of operations"""

    def __init__(self, slow_threshold_ms: float = 100.0):
        self.slow_threshold_ms = slow_threshold_ms
        self._metrics = {}

    @contextmanager
    def track(self, name: str):
        """Context manager to track operation duration"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self._metrics[name] = {"duration_ms": duration_ms}

    def get_metrics(self) -> dict:
        """Get all tracked metrics"""
        return self._metrics.copy()

    def get_slow_operations(self) -> list:
        """Get operations exceeding threshold"""
        slow_ops = []
        for name, metrics in self._metrics.items():
            if metrics["duration_ms"] > self.slow_threshold_ms:
                slow_ops.append({"name": name, "duration_ms": metrics["duration_ms"]})
        return slow_ops
