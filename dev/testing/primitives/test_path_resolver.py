"""
TDD Red-Phase Tests for PathResolver Primitive

Issue: #9 - [Sprint 1, Day 4] Primitive: PathResolver
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 7 tests mapping 1:1 to 7 acceptance criteria
"""

import re
import uuid
from pathlib import Path

import pytest


class TestPathResolver:
    """Test suite for PathResolver primitive - Red Phase"""

    def test_get_project_root_detects_git_marker(self, tmp_path):
        """
        AC1: Detects project root correctly (.git, pyproject.toml, package.json)

        Verifies PathResolver detects project root via .git directory marker
        """
        # Arrange: Create project structure with .git marker
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        git_dir = project_root / ".git"
        git_dir.mkdir()

        # Create subdirectory to test upward traversal
        sub_dir = project_root / "src" / "components"
        sub_dir.mkdir(parents=True)

        # Act: Get project root from subdirectory
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        detected_root = resolver.get_project_root(start_path=sub_dir)

        # Assert: Detected root matches actual project root
        assert detected_root == project_root
        assert detected_root.exists()
        assert (detected_root / ".git").exists()

    def test_get_project_root_detects_pyproject_marker(self, tmp_path):
        """
        AC1: Detects project root correctly (pyproject.toml marker)

        Verifies PathResolver detects project root via pyproject.toml marker
        """
        # Arrange: Create project structure with pyproject.toml marker
        project_root = tmp_path / "python-project"
        project_root.mkdir()
        pyproject_file = project_root / "pyproject.toml"
        pyproject_file.write_text("[tool.poetry]\nname = 'test'\n", encoding="utf-8")

        # Create subdirectory
        sub_dir = project_root / "src"
        sub_dir.mkdir()

        # Act: Get project root from subdirectory
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        detected_root = resolver.get_project_root(start_path=sub_dir)

        # Assert: Detected root matches actual project root
        assert detected_root == project_root
        assert (detected_root / "pyproject.toml").exists()

    def test_get_project_root_detects_packagejson_marker(self, tmp_path):
        """
        AC1: Detects project root correctly (package.json marker)

        Verifies PathResolver detects project root via package.json marker
        """
        # Arrange: Create project structure with package.json marker
        project_root = tmp_path / "node-project"
        project_root.mkdir()
        package_file = project_root / "package.json"
        package_file.write_text('{"name": "test"}', encoding="utf-8")

        # Create deep subdirectory
        sub_dir = project_root / "src" / "components" / "ui"
        sub_dir.mkdir(parents=True)

        # Act: Get project root from deep subdirectory
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        detected_root = resolver.get_project_root(start_path=sub_dir)

        # Assert: Detected root matches actual project root
        assert detected_root == project_root
        assert (detected_root / "package.json").exists()

    def test_get_project_root_falls_back_to_cwd_when_no_markers(self, tmp_path):
        """
        AC2: Falls back to cwd if no markers found

        Verifies PathResolver returns current working directory when no markers exist
        """
        # Arrange: Create directory structure with NO project markers
        no_marker_dir = tmp_path / "no-markers"
        no_marker_dir.mkdir()

        # Act: Get project root from directory without markers
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        detected_root = resolver.get_project_root(start_path=no_marker_dir)

        # Assert: Falls back to the starting directory
        assert detected_root == no_marker_dir
        # Verify no markers exist
        assert not (detected_root / ".git").exists()
        assert not (detected_root / "pyproject.toml").exists()
        assert not (detected_root / "package.json").exists()

    def test_create_session_dir_creates_unique_directory_with_timestamp(self, tmp_path):
        """
        AC3: Creates session directory with unique name (agent-name + session-id + timestamp)

        Verifies session directory naming pattern and uniqueness
        Pattern: <root>/.agent-harness/sessions/agent-<name>-session-<uuid>-<timestamp>/
        """
        # Arrange: Use tmp_path as project root
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        agent_name = "test-agent"

        # Act: Create session directory
        session_dir = resolver.create_session_dir(project_root=tmp_path, agent_name=agent_name)

        # Assert: Directory exists
        assert session_dir.exists()
        assert session_dir.is_dir()

        # Assert: Path structure matches expected pattern
        assert session_dir.parent.parent.parent == tmp_path
        assert session_dir.parent.parent.name == "sessions"
        assert session_dir.parent.parent.parent.name == ".agent-harness"

        # Assert: Directory name matches pattern: agent-<name>-session-<uuid>-<timestamp>
        dir_name = session_dir.name
        pattern = r"^agent-test-agent-session-[a-f0-9-]+-\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*$"
        assert re.match(pattern, dir_name), f"Directory name '{dir_name}' doesn't match pattern"

        # Assert: UUID portion is valid
        uuid_match = re.search(r"session-([a-f0-9-]+)-\d{4}", dir_name)
        assert uuid_match, "UUID not found in directory name"
        uuid_str = uuid_match.group(1)
        try:
            uuid.UUID(uuid_str)  # Validates UUID format
        except ValueError:
            pytest.fail(f"Invalid UUID format: {uuid_str}")

        # Assert: No collisions - create second session, should be different
        session_dir_2 = resolver.create_session_dir(project_root=tmp_path, agent_name=agent_name)
        assert session_dir != session_dir_2, "Session directories should be unique"

    def test_create_pod_dir_creates_directory_with_timestamp(self, tmp_path):
        """
        AC4: Creates pod directory with unique name (pod-name + timestamp)

        Verifies pod directory creation within session directory
        Pattern: <session>/pods/pod-<name>-<timestamp>/
        """
        # Arrange: Create session directory first
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        session_dir = tmp_path / "session-test"
        session_dir.mkdir(parents=True)
        pod_name = "test-pod"

        # Act: Create pod directory
        pod_dir = resolver.create_pod_dir(session_dir=session_dir, pod_name=pod_name)

        # Assert: Directory exists
        assert pod_dir.exists()
        assert pod_dir.is_dir()

        # Assert: Path structure matches expected pattern
        assert pod_dir.parent.parent == session_dir
        assert pod_dir.parent.name == "pods"

        # Assert: Directory name matches pattern: pod-<name>-<timestamp>
        dir_name = pod_dir.name
        pattern = r"^pod-test-pod-\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*$"
        assert re.match(pattern, dir_name), f"Pod directory name '{dir_name}' doesn't match pattern"

        # Assert: No collisions
        pod_dir_2 = resolver.create_pod_dir(session_dir=session_dir, pod_name=pod_name)
        assert pod_dir != pod_dir_2, "Pod directories should be unique"

    def test_create_worker_dir_creates_directory_with_timestamp(self, tmp_path):
        """
        AC5: Creates worker directory with unique name (worker-id + timestamp)

        Verifies worker directory creation within pod directory
        Pattern: <pod>/workers/worker-<id>-<timestamp>/
        """
        # Arrange: Create pod directory first
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()
        pod_dir = tmp_path / "pod-test"
        pod_dir.mkdir(parents=True)
        worker_id = "worker-001"

        # Act: Create worker directory
        worker_dir = resolver.create_worker_dir(pod_dir=pod_dir, worker_id=worker_id)

        # Assert: Directory exists
        assert worker_dir.exists()
        assert worker_dir.is_dir()

        # Assert: Path structure matches expected pattern
        assert worker_dir.parent.parent == pod_dir
        assert worker_dir.parent.name == "workers"

        # Assert: Directory name matches pattern: worker-<id>-<timestamp>
        dir_name = worker_dir.name
        pattern = r"^worker-worker-001-\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*$"
        assert re.match(
            pattern, dir_name
        ), f"Worker directory name '{dir_name}' doesn't match pattern"

        # Assert: No collisions
        worker_dir_2 = resolver.create_worker_dir(pod_dir=pod_dir, worker_id=worker_id)
        assert worker_dir != worker_dir_2, "Worker directories should be unique"

    def test_gitignore_auto_created_in_agent_harness_directory(self, tmp_path):
        """
        AC7: Auto-creates .gitignore in .agent-harness/

        Verifies .gitignore is created to ignore all session data
        """
        # Arrange: Use tmp_path as project root
        from src.primitives.path_resolver import PathResolver

        resolver = PathResolver()

        # Act: Create session directory (should auto-create .gitignore)
        session_dir = resolver.create_session_dir(project_root=tmp_path, agent_name="test")

        # Assert: .gitignore exists in .agent-harness/
        gitignore_path = tmp_path / ".agent-harness" / ".gitignore"
        assert gitignore_path.exists(), ".gitignore not created in .agent-harness/"

        # Assert: .gitignore contains patterns to ignore session data
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        assert gitignore_content.strip() != "", ".gitignore is empty"

        # Expected patterns: ignore all sessions
        assert "sessions/" in gitignore_content or "*" in gitignore_content, (
            ".gitignore doesn't ignore sessions/"
        )
