"""Tests for PodMessageQueue primitive"""

import pytest

from src.core.pod_message_queue import PodMessageQueue


class TestPodMessageQueue:
    """Test suite for PodMessageQueue"""

    def test_send_message(self):
        """Test sending a message between pods"""
        queue = PodMessageQueue()
        queue.send("pod1", "pod2", {"task": "process"})

        assert "pod2" in queue._queues
        assert len(queue._queues["pod2"]) == 1
        assert queue._queues["pod2"][0] == {
            "from": "pod1",
            "to": "pod2",
            "payload": {"task": "process"},
        }

    def test_send_multiple_messages(self):
        """Test sending multiple messages to same pod"""
        queue = PodMessageQueue()
        queue.send("pod1", "pod2", {"task": "first"})
        queue.send("pod1", "pod2", {"task": "second"})

        assert len(queue._queues["pod2"]) == 2

    def test_receive_message(self):
        """Test receiving a message from queue"""
        queue = PodMessageQueue()
        queue.send("pod1", "pod2", {"task": "process"})

        msg = queue.receive("pod2")
        assert msg == {"from": "pod1", "to": "pod2", "payload": {"task": "process"}}
        assert len(queue._queues["pod2"]) == 0

    def test_receive_empty_queue(self):
        """Test receiving from empty queue returns None"""
        queue = PodMessageQueue()
        msg = queue.receive("pod_nonexistent")

        assert msg is None

    def test_receive_empty_existing_queue(self):
        """Test receiving from empty but existing queue returns None"""
        queue = PodMessageQueue()
        queue.send("pod1", "pod2", {"task": "process"})
        queue.receive("pod2")  # Empty the queue

        msg = queue.receive("pod2")
        assert msg is None

    def test_fifo_order(self):
        """Test messages are received in FIFO order"""
        queue = PodMessageQueue()
        queue.send("pod1", "pod2", {"task": "first"})
        queue.send("pod1", "pod2", {"task": "second"})
        queue.send("pod1", "pod2", {"task": "third"})

        msg1 = queue.receive("pod2")
        msg2 = queue.receive("pod2")
        msg3 = queue.receive("pod2")

        assert msg1["payload"]["task"] == "first"
        assert msg2["payload"]["task"] == "second"
        assert msg3["payload"]["task"] == "third"

    def test_multiple_queues(self):
        """Test multiple independent pod queues"""
        queue = PodMessageQueue()
        queue.send("pod1", "pod2", {"task": "to_pod2"})
        queue.send("pod1", "pod3", {"task": "to_pod3"})

        msg2 = queue.receive("pod2")
        msg3 = queue.receive("pod3")

        assert msg2["payload"]["task"] == "to_pod2"
        assert msg3["payload"]["task"] == "to_pod3"
