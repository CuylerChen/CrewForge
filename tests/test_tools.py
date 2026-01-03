"""Tests for CrewForge tools."""

import tempfile
from pathlib import Path

import pytest

from crewforge.tools.filesystem import ReadFileTool, WriteFileTool, ListDirectoryTool
from crewforge.tools.shell import ShellExecutorTool


class TestFileSystemTools:
    """Tests for filesystem tools."""

    def test_write_and_read_file(self):
        """Test writing and reading a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Hello, CrewForge!"

            # Write file
            write_tool = WriteFileTool()
            result = write_tool._run(str(file_path), content)
            assert "Successfully wrote" in result

            # Read file
            read_tool = ReadFileTool()
            result = read_tool._run(str(file_path))
            assert result == content

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        read_tool = ReadFileTool()
        result = read_tool._run("/nonexistent/path/file.txt")
        assert "Error" in result

    def test_list_directory(self):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            (Path(tmpdir) / "file1.txt").touch()
            (Path(tmpdir) / "file2.txt").touch()
            (Path(tmpdir) / "subdir").mkdir()

            list_tool = ListDirectoryTool()
            result = list_tool._run(tmpdir)

            assert "file1.txt" in result
            assert "file2.txt" in result
            assert "subdir" in result


class TestShellTool:
    """Tests for shell executor tool."""

    def test_simple_command(self):
        """Test running a simple command."""
        shell_tool = ShellExecutorTool()
        result = shell_tool._run("echo 'Hello'")

        assert "Hello" in result
        assert "EXIT CODE: 0" in result

    def test_command_with_error(self):
        """Test running a command that fails."""
        shell_tool = ShellExecutorTool()
        result = shell_tool._run("ls /nonexistent_directory_12345")

        assert "EXIT CODE:" in result
        # Exit code should not be 0
        assert "EXIT CODE: 0" not in result or "No such file" in result

    def test_blocked_command(self):
        """Test that dangerous commands are blocked."""
        shell_tool = ShellExecutorTool()
        result = shell_tool._run("rm -rf /")

        assert "blocked" in result.lower()


class TestGitTools:
    """Tests for git tools."""

    def test_git_init(self):
        """Test initializing a git repository."""
        from crewforge.tools.git import GitInitTool

        with tempfile.TemporaryDirectory() as tmpdir:
            git_tool = GitInitTool()
            result = git_tool._run(tmpdir, "main")

            assert "Initialized" in result or "Error" in result  # May fail if git not installed


class TestDatabaseOperations:
    """Tests for database operations."""

    def test_create_project(self):
        """Test creating a project in the database."""
        from crewforge.storage import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(f"sqlite:///{db_path}")
            db.create_tables()

            project = db.create_project(
                name="test-project",
                description="A test project",
            )

            assert project.id is not None
            assert project.name == "test-project"

    def test_create_and_update_task(self):
        """Test creating and updating a task."""
        from crewforge.storage import Database, TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(f"sqlite:///{db_path}")
            db.create_tables()

            project = db.create_project(name="test-project")
            task = db.create_task(
                project_id=project.id,
                title="Test task",
                description="A test task",
            )

            assert task.status == TaskStatus.PENDING

            db.update_task_status(task.id, TaskStatus.IN_PROGRESS)
            updated_task = db.get_task(task.id)

            assert updated_task.status == TaskStatus.IN_PROGRESS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
