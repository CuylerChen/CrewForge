"""Core CrewAI orchestration for CrewForge."""

from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from crewai import Crew, Task, Process
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import get_settings, get_llm_config
from ..storage import get_database, TaskStatus, ProjectStatus
from .manager import ManagerAgent
from .agents import (
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    TesterAgent,
    DevOpsAgent,
)


console = Console()


class CrewForgeOrchestrator:
    """Main orchestrator for CrewForge multi-agent development."""

    def __init__(
        self,
        project_name: str,
        project_path: Optional[str] = None,
        verbose: bool = False,
        on_approval_needed: Optional[Callable[[str, str], bool]] = None,
    ):
        """Initialize the orchestrator.

        Args:
            project_name: Name of the project
            project_path: Path to the project directory (defaults to cwd/project_name)
            verbose: Enable verbose output
            on_approval_needed: Callback for approval requests (type, content) -> approved
        """
        self.project_name = project_name
        self.project_path = Path(project_path) if project_path else Path.cwd() / project_name
        self.verbose = verbose
        self.on_approval_needed = on_approval_needed or self._default_approval

        self.settings = get_settings()
        self.llm_config = get_llm_config()
        self.db = get_database()

        # Initialize project in database
        self.project = self._init_project()

        # Initialize agents
        self._init_agents()

    def _init_project(self):
        """Initialize or load project from database."""
        existing = self.db.get_project_by_name(self.project_name)
        if existing:
            console.print(f"[yellow]Resuming existing project:[/] {self.project_name}")
            return existing

        project = self.db.create_project(
            name=self.project_name,
            git_repo_path=str(self.project_path),
        )
        console.print(f"[green]Created new project:[/] {self.project_name}")
        return project

    def _init_agents(self):
        """Initialize all agents."""
        project_str = str(self.project_path)

        self.manager = ManagerAgent(project_str, self.verbose)
        self.architect = ArchitectAgent(project_str, self.verbose)
        self.developer = DeveloperAgent(project_str, self.verbose)
        self.reviewer = ReviewerAgent(project_str, self.verbose)
        self.tester = TesterAgent(project_str, self.verbose)
        self.devops = DevOpsAgent(project_str, self.verbose)

        self.agents = {
            "manager": self.manager,
            "architect": self.architect,
            "developer": self.developer,
            "reviewer": self.reviewer,
            "tester": self.tester,
            "devops": self.devops,
        }

    def _default_approval(self, approval_type: str, content: str) -> bool:
        """Default approval callback that prompts the user."""
        console.print(Panel(content, title=f"[bold]{approval_type}[/]"))
        response = console.input("[bold yellow]Approve? (y/n): [/]")
        return response.lower().strip() in ("y", "yes")

    def run(self, requirements: str) -> dict:
        """Run the full development workflow.

        Args:
            requirements: Project requirements description

        Returns:
            dict with status and results
        """
        console.print(Panel(
            f"[bold blue]Starting CrewForge[/]\n\n"
            f"Project: {self.project_name}\n"
            f"Path: {self.project_path}",
            title="CrewForge"
        ))

        # Ensure project directory exists
        self.project_path.mkdir(parents=True, exist_ok=True)

        results = {
            "project_name": self.project_name,
            "project_path": str(self.project_path),
            "status": "started",
            "phases": {},
        }

        try:
            # Phase 1: Requirements confirmation
            if self.settings.require_requirement_approval:
                if not self._confirm_requirements(requirements):
                    results["status"] = "cancelled"
                    results["message"] = "Requirements not approved"
                    return results

            # Phase 2: Architecture design
            architecture = self._design_architecture(requirements)
            results["phases"]["architecture"] = architecture

            if self.settings.require_architecture_approval:
                if not self._confirm_architecture(architecture):
                    results["status"] = "cancelled"
                    results["message"] = "Architecture not approved"
                    return results

            # Phase 3: Task breakdown and execution
            tasks = self._break_down_tasks(requirements, architecture)
            results["phases"]["task_breakdown"] = tasks

            # Phase 4: Implementation
            implementation = self._run_implementation(tasks)
            results["phases"]["implementation"] = implementation

            # Phase 5: Testing
            testing = self._run_testing()
            results["phases"]["testing"] = testing

            # Phase 6: Final merge to main
            self._finalize_project()
            results["status"] = "completed"

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            console.print(f"[red]Error: {e}[/]")

        return results

    def _confirm_requirements(self, requirements: str) -> bool:
        """Confirm requirements with user."""
        console.print("\n[bold]Phase 1: Requirements Confirmation[/]\n")

        # Store requirements
        self.db.update_project_requirements(self.project.id, requirements)
        self.db.update_project_status(self.project.id, ProjectStatus.REQUIREMENTS_PENDING)

        approved = self.on_approval_needed("Requirements Review", requirements)

        if approved:
            self.db.update_project_requirements(self.project.id, requirements, approved=True)
            self.db.update_project_status(self.project.id, ProjectStatus.REQUIREMENTS_APPROVED)
            console.print("[green]Requirements approved[/]")
        else:
            console.print("[red]Requirements rejected[/]")

        return approved

    def _design_architecture(self, requirements: str) -> str:
        """Design system architecture using the Architect agent."""
        console.print("\n[bold]Phase 2: Architecture Design[/]\n")

        self.db.update_project_status(self.project.id, ProjectStatus.ARCHITECTURE_PENDING)

        # Create architecture task - Architect analyzes requirements and recommends tech stack
        arch_task = Task(
            description=f"""Analyze the following requirements and design the software architecture:

{requirements}

## Your Tasks:

### 1. Determine Project Type
First, analyze what type of project this is:
- Frontend only (web app, mobile app, browser extension)
- Backend only (API, CLI tool, library, daemon service)
- Full-stack (frontend + backend)
- Other (data pipeline, ML model, infrastructure, etc.)

### 2. Recommend Technology Stack
Based on the requirements, recommend the most suitable tech stack.
Be specific and practical. Consider:
- Project complexity and scale
- Team expertise (if mentioned)
- Performance requirements
- Deployment environment

Format your tech stack recommendation as:
```yaml
tech_stack:
  type: frontend-only | backend-only | fullstack | cli | library | other
  # Include only relevant sections based on type:
  frontend:  # if applicable
    language: ...
    framework: ...
    build_tool: ...
  backend:   # if applicable
    language: ...
    framework: ...
  database:  # if applicable
    type: ...
    name: ...
  infrastructure:  # if applicable
    ...
```

### 3. System Design
Provide:
1. System overview and high-level design
2. Component structure and interactions
3. Data models and storage design (if applicable)
4. API design (if applicable)
5. File/folder structure
6. Key design decisions and rationale

Create clear documentation that developers can follow.""",
            expected_output="Tech stack recommendation (in YAML format) followed by detailed architecture document",
            agent=self.architect.create_agent(),
        )

        # Run the architecture crew
        crew = Crew(
            agents=[self.architect.create_agent()],
            tasks=[arch_task],
            verbose=self.verbose,
            process=Process.sequential,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Designing architecture...", total=None)
            result = crew.kickoff()

        architecture = str(result)
        self.db.update_project_architecture(self.project.id, architecture)

        # Extract and save tech_stack to crewforge.yaml
        self._save_tech_stack(architecture)

        console.print("[green]Architecture design completed[/]")
        return architecture

    def _save_tech_stack(self, architecture: str):
        """Extract tech_stack from architecture and save to crewforge.yaml."""
        import yaml
        import re

        config_path = self.project_path / "crewforge.yaml"
        if not config_path.exists():
            return

        # Try to extract tech_stack YAML block from architecture
        yaml_pattern = r"```yaml\s*\n(tech_stack:.*?)```"
        match = re.search(yaml_pattern, architecture, re.DOTALL)

        if match:
            try:
                tech_stack_yaml = match.group(1)
                tech_stack_data = yaml.safe_load(tech_stack_yaml)

                # Load existing config
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}

                # Update tech_stack
                if tech_stack_data and "tech_stack" in tech_stack_data:
                    config["tech_stack"] = tech_stack_data["tech_stack"]
                elif tech_stack_data:
                    config["tech_stack"] = tech_stack_data

                # Save updated config
                with open(config_path, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

                console.print("[dim]Tech stack saved to crewforge.yaml[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not parse tech stack: {e}[/]")

    def _confirm_architecture(self, architecture: str) -> bool:
        """Confirm architecture with user."""
        approved = self.on_approval_needed("Architecture Review", architecture)

        if approved:
            self.db.update_project_architecture(self.project.id, architecture, approved=True)
            self.db.update_project_status(self.project.id, ProjectStatus.ARCHITECTURE_APPROVED)
            console.print("[green]Architecture approved[/]")
        else:
            console.print("[red]Architecture rejected[/]")

        return approved

    def _break_down_tasks(self, requirements: str, architecture: str) -> list:
        """Break down requirements into tasks using Manager agent."""
        console.print("\n[bold]Phase 3: Task Breakdown[/]\n")

        breakdown_task = Task(
            description=self.manager.create_task_breakdown_prompt(
                f"Requirements:\n{requirements}\n\nArchitecture:\n{architecture}"
            ),
            expected_output="Structured list of development tasks with assignments",
            agent=self.manager.create_agent(),
        )

        crew = Crew(
            agents=[self.manager.create_agent()],
            tasks=[breakdown_task],
            verbose=self.verbose,
            process=Process.sequential,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Breaking down tasks...", total=None)
            result = crew.kickoff()

        task_breakdown = str(result)
        console.print("[green]Task breakdown completed[/]")
        return self._parse_tasks(task_breakdown)

    def _parse_tasks(self, task_breakdown: str) -> list:
        """Parse task breakdown into structured tasks."""
        # Simple parsing - in production, use structured output
        tasks = []
        lines = task_breakdown.split("\n")
        current_task = {}

        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                if current_task:
                    tasks.append(current_task)
                current_task = {"title": line[2:], "description": ""}
            elif current_task and line:
                current_task["description"] += line + " "

        if current_task:
            tasks.append(current_task)

        # Create tasks in database
        for task_data in tasks:
            self.db.create_task(
                project_id=self.project.id,
                title=task_data.get("title", "Untitled"),
                description=task_data.get("description", ""),
            )

        return tasks

    def _run_implementation(self, tasks: list) -> dict:
        """Run the implementation phase with hierarchical delegation."""
        console.print("\n[bold]Phase 4: Implementation[/]\n")

        self.db.update_project_status(self.project.id, ProjectStatus.DEVELOPING)

        # Create the implementation crew with hierarchical process
        # Note: manager_agent should NOT be in the agents list for hierarchical mode
        # and manager_agent cannot have tools
        crew = Crew(
            agents=[
                self.developer.create_agent(),
                self.reviewer.create_agent(),
            ],
            tasks=self._create_implementation_tasks(tasks),
            verbose=self.verbose,
            process=Process.hierarchical,
            manager_agent=self.manager.create_agent(as_manager=True),
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Implementing features...", total=None)
            result = crew.kickoff()

        console.print("[green]Implementation completed[/]")
        return {"result": str(result)}

    def _create_implementation_tasks(self, tasks: list) -> list:
        """Create CrewAI tasks for implementation."""
        crewai_tasks = []

        for task_data in tasks:
            task = Task(
                description=f"""Implement the following:

Title: {task_data.get('title', 'Task')}
Description: {task_data.get('description', '')}

Requirements:
1. Write clean, well-documented code
2. Follow the architectural guidelines
3. Include appropriate error handling
4. Write unit tests for new code
5. Commit changes with meaningful messages""",
                expected_output="Implemented feature with tests and documentation",
                agent=self.developer.create_agent(),
            )
            crewai_tasks.append(task)

        return crewai_tasks

    def _run_testing(self) -> dict:
        """Run the testing phase."""
        console.print("\n[bold]Phase 5: Testing[/]\n")

        self.db.update_project_status(self.project.id, ProjectStatus.TESTING)

        test_task = Task(
            description="""Run all tests and verify the implementation:

1. Run unit tests
2. Run integration tests if available
3. Perform E2E testing for web interfaces
4. Check test coverage
5. Report any failures or issues""",
            expected_output="Test results with coverage report",
            agent=self.tester.create_agent(),
        )

        crew = Crew(
            agents=[self.tester.create_agent()],
            tasks=[test_task],
            verbose=self.verbose,
            process=Process.sequential,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Running tests...", total=None)
            result = crew.kickoff()

        console.print("[green]Testing completed[/]")
        return {"result": str(result)}

    def _finalize_project(self):
        """Finalize project by merging to main."""
        console.print("\n[bold]Phase 6: Finalization[/]\n")

        self.db.update_project_status(self.project.id, ProjectStatus.COMPLETED)
        console.print(f"[green bold]Project {self.project_name} completed successfully![/]")

    def resume(self, task_id: Optional[int] = None) -> dict:
        """Resume a previously interrupted project.

        Args:
            task_id: Specific task to resume from (optional)

        Returns:
            dict with status and results
        """
        console.print(f"[yellow]Resuming project: {self.project_name}[/]")

        # Get project status
        project = self.db.get_project(self.project.id)
        if not project:
            return {"status": "error", "message": "Project not found"}

        # Get pending tasks
        pending_tasks = self.db.get_pending_tasks(project.id)

        if not pending_tasks:
            return {"status": "completed", "message": "No pending tasks"}

        console.print(f"Found {len(pending_tasks)} pending tasks")

        # Resume from where we left off based on project status
        if project.status == ProjectStatus.REQUIREMENTS_PENDING:
            return self.run(project.requirements or "")
        elif project.status == ProjectStatus.ARCHITECTURE_PENDING:
            architecture = self._design_architecture(project.requirements or "")
            # Continue with implementation...

        return {"status": "resumed", "pending_tasks": len(pending_tasks)}

    def get_status(self) -> dict:
        """Get current project status."""
        project = self.db.get_project(self.project.id)
        tasks = self.db.get_project_tasks(self.project.id)

        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        failed = [t for t in tasks if t.status == TaskStatus.FAILED]

        return {
            "project_name": project.name,
            "status": project.status.value if project else "unknown",
            "tasks": {
                "total": len(tasks),
                "completed": len(completed),
                "pending": len(pending),
                "in_progress": len(in_progress),
                "failed": len(failed),
            },
        }
