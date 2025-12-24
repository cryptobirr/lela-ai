"""Pod state management for tracking multiple pods"""


class PodStateManager:
    """Tracks state across multiple pods"""

    def __init__(self, session_dir):
        self.session_dir = session_dir
        self._pods = {}
        self._statuses = {}

    def register_pod(self, name: str, path) -> None:
        """Register a pod for tracking"""
        self._pods[name] = path
        self._statuses[name] = "registered"

    def update_status(self, name: str, status: str) -> None:
        """Update pod status"""
        self._statuses[name] = status

    def get_status(self, name: str) -> str:
        """Get current status for a pod"""
        return self._statuses.get(name, "unknown")

    def get_all_statuses(self) -> dict:
        """Get all pod statuses"""
        return self._statuses.copy()
