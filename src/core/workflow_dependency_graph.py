"""Workflow dependency tracking and cascading failure handling"""


class WorkflowDependencyGraph:
    """Manages workflow dependencies and propagates failures"""

    def __init__(self):
        self._workflows = {}
        self._dependencies = {}
        self._statuses = {}
        self._cancelled_due_to_dependency = set()

    def add_workflow(self, name: str, dependencies: list) -> None:
        """Add workflow with its dependencies"""
        self._workflows[name] = dependencies
        self._dependencies[name] = dependencies
        self._statuses[name] = "pending"

    def mark_failed(self, name: str, reason: str = None) -> None:
        """Mark workflow as failed and cascade to dependents"""
        self._statuses[name] = "failed"
        # Find all workflows that depend on this one
        for workflow, deps in self._dependencies.items():
            if name in deps:
                self._statuses[workflow] = "cancelled"
                self._cancelled_due_to_dependency.add(workflow)

    def get_status(self, name: str) -> str:
        """Get workflow status"""
        return self._statuses.get(name, "unknown")

    def was_cancelled_due_to_dependency(self, name: str) -> bool:
        """Check if workflow was cancelled due to dependency failure"""
        return name in self._cancelled_due_to_dependency
