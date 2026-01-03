"""Shell execution tool for agents."""

import subprocess
import shlex
from pathlib import Path
from typing import ClassVar, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ShellCommandInput(BaseModel):
    """Input schema for shell command execution."""

    command: str = Field(..., description="The shell command to execute")
    working_dir: Optional[str] = Field(
        default=None, description="Working directory for command execution"
    )
    timeout: int = Field(
        default=300, description="Timeout in seconds for command execution"
    )


class ShellExecutorTool(BaseTool):
    """Tool to execute shell commands."""

    name: str = "execute_shell"
    description: str = """Execute a shell command and return the output.
    Use this to run build commands, tests, install dependencies, etc.
    Be careful with destructive commands."""
    args_schema: Type[BaseModel] = ShellCommandInput

    # Blocked commands for safety
    BLOCKED_COMMANDS: ClassVar[list[str]] = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        ":(){:|:&};:",  # Fork bomb
        "dd if=/dev/zero",
        "chmod -R 777 /",
    ]

    def _run(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: int = 300,
    ) -> str:
        """Execute shell command."""
        # Safety check
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return f"Error: Command contains blocked pattern '{blocked}'"

        try:
            # Determine working directory
            cwd = Path(working_dir) if working_dir else Path.cwd()
            if not cwd.exists():
                return f"Error: Working directory '{cwd}' does not exist."

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output_parts = []

            if result.stdout:
                output_parts.append(f"STDOUT:\n{result.stdout}")

            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")

            output_parts.append(f"EXIT CODE: {result.returncode}")

            return "\n\n".join(output_parts)

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"


class MultiCommandInput(BaseModel):
    """Input schema for multiple shell commands."""

    commands: list[str] = Field(..., description="List of shell commands to execute")
    working_dir: Optional[str] = Field(
        default=None, description="Working directory for command execution"
    )
    stop_on_error: bool = Field(
        default=True, description="Stop execution if a command fails"
    )


class MultiShellExecutorTool(BaseTool):
    """Tool to execute multiple shell commands sequentially."""

    name: str = "execute_shell_multi"
    description: str = """Execute multiple shell commands sequentially.
    Optionally stop on first error."""
    args_schema: Type[BaseModel] = MultiCommandInput

    def _run(
        self,
        commands: list[str],
        working_dir: Optional[str] = None,
        stop_on_error: bool = True,
    ) -> str:
        """Execute multiple shell commands."""
        shell_tool = ShellExecutorTool()
        results = []

        for i, command in enumerate(commands, 1):
            result = shell_tool._run(command=command, working_dir=working_dir)
            results.append(f"=== Command {i}: {command} ===\n{result}")

            # Check for error
            if stop_on_error and "EXIT CODE: 0" not in result:
                results.append(f"\nStopped at command {i} due to error.")
                break

        return "\n\n".join(results)
