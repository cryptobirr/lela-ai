"""Pod message queue for inter-pod communication"""


class PodMessageQueue:
    """Queue for sending/receiving messages between pods"""

    def __init__(self):
        self._queues = {}

    def send(self, from_pod: str, to_pod: str, payload: dict) -> None:
        """Send message from one pod to another"""
        if to_pod not in self._queues:
            self._queues[to_pod] = []
        self._queues[to_pod].append({"from": from_pod, "to": to_pod, "payload": payload})

    def receive(self, pod: str) -> dict:
        """Receive next message for a pod"""
        if pod not in self._queues or not self._queues[pod]:
            return None
        return self._queues[pod].pop(0)
