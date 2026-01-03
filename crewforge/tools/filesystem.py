"""File system tools for agents."""

from pathlib import Path
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    """Input schema for reading a file."""

    file_path: str = Field(..., description="Path to the file to read")


class ReadFileTool(BaseTool):
    """Tool to read file contents."""

    name: str = "read_file"
    description: str = "Read the contents of a file. Returns the file content as a string."
    args_schema: Type[BaseModel] = ReadFileInput

    def _run(self, file_path: str) -> str:
        """Read file contents."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File '{file_path}' does not exist."
            if not path.is_file():
                return f"Error: '{file_path}' is not a file."
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {str(e)}"


class WriteFileInput(BaseModel):
    """Input schema for writing a file."""

    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    create_dirs: bool = Field(
        default=True, description="Create parent directories if they don't exist"
    )


class WriteFileTool(BaseTool):
    """Tool to write content to a file."""

    name: str = "write_file"
    description: str = "Write content to a file. Creates the file if it doesn't exist."
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(self, file_path: str, content: str, create_dirs: bool = True) -> str:
        """Write content to file."""
        try:
            path = Path(file_path)
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Successfully wrote to '{file_path}'"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class ListDirectoryInput(BaseModel):
    """Input schema for listing directory contents."""

    directory_path: str = Field(..., description="Path to the directory to list")
    recursive: bool = Field(default=False, description="Whether to list recursively")
    pattern: str = Field(default="*", description="Glob pattern to filter files")


class ListDirectoryTool(BaseTool):
    """Tool to list directory contents."""

    name: str = "list_directory"
    description: str = "List files and directories in a given path."
    args_schema: Type[BaseModel] = ListDirectoryInput

    def _run(
        self, directory_path: str, recursive: bool = False, pattern: str = "*"
    ) -> str:
        """List directory contents."""
        try:
            path = Path(directory_path)
            if not path.exists():
                return f"Error: Directory '{directory_path}' does not exist."
            if not path.is_dir():
                return f"Error: '{directory_path}' is not a directory."

            if recursive:
                items = list(path.rglob(pattern))
            else:
                items = list(path.glob(pattern))

            result = []
            for item in sorted(items):
                relative = item.relative_to(path)
                prefix = "[DIR] " if item.is_dir() else "[FILE]"
                result.append(f"{prefix} {relative}")

            if not result:
                return f"No items found in '{directory_path}'"
            return "\n".join(result)
        except Exception as e:
            return f"Error listing directory: {str(e)}"


class CreateDirectoryInput(BaseModel):
    """Input schema for creating a directory."""

    directory_path: str = Field(..., description="Path to the directory to create")


class CreateDirectoryTool(BaseTool):
    """Tool to create directories."""

    name: str = "create_directory"
    description: str = "Create a new directory (including parent directories)."
    args_schema: Type[BaseModel] = CreateDirectoryInput

    def _run(self, directory_path: str) -> str:
        """Create directory."""
        try:
            path = Path(directory_path)
            path.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory '{directory_path}'"
        except Exception as e:
            return f"Error creating directory: {str(e)}"


class DeleteFileInput(BaseModel):
    """Input schema for deleting a file."""

    file_path: str = Field(..., description="Path to the file to delete")


class DeleteFileTool(BaseTool):
    """Tool to delete a file."""

    name: str = "delete_file"
    description: str = "Delete a file from the filesystem."
    args_schema: Type[BaseModel] = DeleteFileInput

    def _run(self, file_path: str) -> str:
        """Delete file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File '{file_path}' does not exist."
            if path.is_dir():
                return f"Error: '{file_path}' is a directory. Use delete_directory instead."
            path.unlink()
            return f"Successfully deleted '{file_path}'"
        except Exception as e:
            return f"Error deleting file: {str(e)}"


class FileSystemTool:
    """Collection of filesystem tools."""

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """Get all filesystem tools."""
        return [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            CreateDirectoryTool(),
            DeleteFileTool(),
        ]
