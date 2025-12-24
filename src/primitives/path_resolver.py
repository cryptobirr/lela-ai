"""PathResolver Primitive - Issue #9

Resolve project root and create session/pod/worker directories.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path


class PathResolver:
    """Resolve project root and create isolated directory structures"""

    def get_project_root(self, start_path: Path) -> Path:
        """Detect project root by looking for markers (.git, pyproject.toml, package.json)

        Args:
            start_path: Directory to start searching from

        Returns:
            Path: Project root directory, or start_path if no markers found
        """
        current = start_path.resolve()
        markers = [".git", "pyproject.toml", "package.json"]

        # Traverse upward looking for project markers
        while True:
            # Check if any marker exists in current directory
            for marker in markers:
                if (current / marker).exists():
                    return current

            # If we've reached root and found nothing, return start_path
            parent = current.parent
            if parent == current:
                return start_path

            current = parent

    def create_session_dir(self, project_root: Path, agent_name: str) -> Path:
        """Create isolated session directory with unique name

        Pattern: .agent-harness/sessions/agent-<name>-session-<uuid>-<timestamp>/

        Args:
            project_root: Project root directory
            agent_name: Name of the agent

        Returns:
            Path: Created session directory
        """
        # Ensure .agent-harness directory exists under project root
        harness_dir = project_root / ".agent-harness"

        # Create .gitignore to ignore all session data
        gitignore_path = harness_dir / ".gitignore"
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        if not gitignore_path.exists():
            gitignore_path.write_text("sessions/\n", encoding="utf-8")

        # Create sessions directory
        sessions_dir = harness_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique directory name with UUID and timestamp
        session_uuid = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        dir_name = f"agent-{agent_name}-session-{session_uuid}-{timestamp}"

        # Create session directory
        session_dir = sessions_dir / dir_name
        session_dir.mkdir(parents=True, exist_ok=True)

        return session_dir

    def create_pod_dir(self, session_dir: Path, pod_name: str) -> Path:
        """Create isolated pod directory with timestamp

        Pattern: <session>/pods/pod-<name>-<timestamp>/

        Args:
            session_dir: Session directory
            pod_name: Name of the pod

        Returns:
            Path: Created pod directory
        """
        # Create pods directory
        pods_dir = session_dir / "pods"
        pods_dir.mkdir(exist_ok=True)

        # Generate directory name with timestamp
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        dir_name = f"pod-{pod_name}-{timestamp}"

        # Create pod directory
        pod_dir = pods_dir / dir_name
        pod_dir.mkdir(parents=True)

        return pod_dir

    def create_worker_dir(self, pod_dir: Path, worker_id: str) -> Path:
        """Create isolated worker directory with timestamp

        Pattern: <pod>/workers/worker-<id>-<timestamp>/

        Args:
            pod_dir: Pod directory
            worker_id: ID of the worker

        Returns:
            Path: Created worker directory
        """
        # Create workers directory
        workers_dir = pod_dir / "workers"
        workers_dir.mkdir(exist_ok=True)

        # Generate directory name with timestamp
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        dir_name = f"worker-{worker_id}-{timestamp}"

        # Create worker directory
        worker_dir = workers_dir / dir_name
        worker_dir.mkdir(parents=True)

        return worker_dir
