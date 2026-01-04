"""OpenSpec integration tools for spec-driven development."""

from pathlib import Path
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class OpenSpecWriterInput(BaseModel):
    """Input schema for OpenSpec writer tool."""

    file_type: str = Field(
        description="Type of OpenSpec file: 'spec' for SPEC.md or 'plan' for PLAN.md"
    )
    content: str = Field(description="Content in markdown format")
    project_path: str = Field(description="Project directory path")


class OpenSpecWriterTool(BaseTool):
    """Tool for writing OpenSpec documentation (SPEC.md or PLAN.md)."""

    name: str = "write_openspec"
    description: str = """Write OpenSpec documentation to the project directory.
    Use file_type='spec' for functional requirements (SPEC.md) and
    file_type='plan' for implementation details (PLAN.md).

    SPEC.md should contain:
    - Purpose and scope
    - Functional requirements
    - Non-functional requirements
    - User stories/use cases

    PLAN.md should contain:
    - Architecture overview
    - Component breakdown
    - Data models
    - API design
    - File structure"""
    args_schema: type[BaseModel] = OpenSpecWriterInput

    def _run(self, file_type: str, content: str, project_path: str) -> str:
        """Write OpenSpec file to .openspec directory."""
        try:
            project_dir = Path(project_path)
            project_dir.mkdir(parents=True, exist_ok=True)

            # Create .openspec directory following OpenSpec convention
            openspec_dir = project_dir / ".openspec"
            openspec_dir.mkdir(exist_ok=True)

            # Determine filename based on type
            if file_type.lower() == "spec":
                filename = "SPEC.md"
            elif file_type.lower() == "plan":
                filename = "PLAN.md"
            else:
                return f"Error: Invalid file_type '{file_type}'. Use 'spec' or 'plan'."

            file_path = openspec_dir / filename

            # Add OpenSpec header if not present
            if not content.startswith("# "):
                header = f"# {filename.replace('.md', '')}\n\n"
                content = header + content

            # Write content
            file_path.write_text(content, encoding="utf-8")

            return f"Successfully wrote OpenSpec {filename} to {file_path}"

        except Exception as e:
            return f"Error writing OpenSpec file: {str(e)}"


class OpenSpecReaderInput(BaseModel):
    """Input schema for OpenSpec reader tool."""

    project_path: str = Field(description="Project directory path")
    file_type: Optional[str] = Field(
        default=None,
        description="Optional: 'spec' or 'plan' to read specific file, or None for both"
    )


class OpenSpecReaderTool(BaseTool):
    """Tool for reading existing OpenSpec documentation."""

    name: str = "read_openspec"
    description: str = """Read existing OpenSpec documentation from the project.
    Returns the content of SPEC.md and/or PLAN.md files.
    Use this to understand the current specification before making changes."""
    args_schema: type[BaseModel] = OpenSpecReaderInput

    def _run(self, project_path: str, file_type: Optional[str] = None) -> str:
        """Read OpenSpec files from .openspec directory."""
        try:
            openspec_dir = Path(project_path) / ".openspec"

            if not openspec_dir.exists():
                return "No OpenSpec documentation found. The .openspec directory does not exist."

            result = []

            # Determine which files to read
            if file_type and file_type.lower() == "spec":
                files_to_read = ["SPEC.md"]
            elif file_type and file_type.lower() == "plan":
                files_to_read = ["PLAN.md"]
            else:
                files_to_read = ["SPEC.md", "PLAN.md"]

            # Read each file
            for filename in files_to_read:
                file_path = openspec_dir / filename
                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")
                    result.append(f"=== {filename} ===\n\n{content}\n")

            if not result:
                return f"No OpenSpec files found in {openspec_dir}"

            return "\n".join(result)

        except Exception as e:
            return f"Error reading OpenSpec files: {str(e)}"


class OpenSpecUpdateInput(BaseModel):
    """Input schema for OpenSpec update tool."""

    project_path: str = Field(description="Project directory path")
    file_type: str = Field(description="'spec' or 'plan'")
    section: str = Field(description="Section name to update (e.g., 'Functional Requirements')")
    content: str = Field(description="New content for the section")


class OpenSpecUpdateTool(BaseTool):
    """Tool for updating specific sections of OpenSpec documentation."""

    name: str = "update_openspec_section"
    description: str = """Update a specific section of an OpenSpec document.
    This allows incremental updates without rewriting the entire file.
    Useful when implementation reveals needed specification changes."""
    args_schema: type[BaseModel] = OpenSpecUpdateInput

    def _run(self, project_path: str, file_type: str, section: str, content: str) -> str:
        """Update a section in an OpenSpec file."""
        try:
            openspec_dir = Path(project_path) / ".openspec"

            if not openspec_dir.exists():
                return "Error: No OpenSpec directory found. Create specs first."

            # Determine filename
            filename = "SPEC.md" if file_type.lower() == "spec" else "PLAN.md"
            file_path = openspec_dir / filename

            if not file_path.exists():
                return f"Error: {filename} does not exist. Create it first."

            # Read current content
            current_content = file_path.read_text(encoding="utf-8")

            # Simple section replacement (look for ## Section)
            section_header = f"## {section}"
            if section_header not in current_content:
                # Add new section at the end
                updated_content = current_content.rstrip() + f"\n\n{section_header}\n\n{content}\n"
            else:
                # Replace existing section
                # This is a simple implementation - could be made more robust
                lines = current_content.split('\n')
                new_lines = []
                in_section = False
                section_replaced = False

                for i, line in enumerate(lines):
                    if line.startswith(f"## {section}"):
                        in_section = True
                        new_lines.append(line)
                        new_lines.append("")
                        new_lines.append(content)
                        new_lines.append("")
                        section_replaced = True
                    elif in_section and line.startswith("## "):
                        in_section = False
                        new_lines.append(line)
                    elif not in_section:
                        new_lines.append(line)

                updated_content = '\n'.join(new_lines)

            # Write updated content
            file_path.write_text(updated_content, encoding="utf-8")

            return f"Successfully updated section '{section}' in {filename}"

        except Exception as e:
            return f"Error updating OpenSpec section: {str(e)}"


def get_openspec_tools() -> list[BaseTool]:
    """Get all OpenSpec tools."""
    return [
        OpenSpecWriterTool(),
        OpenSpecReaderTool(),
        OpenSpecUpdateTool(),
    ]
