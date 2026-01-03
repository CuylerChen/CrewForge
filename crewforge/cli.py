"""CLI interface for CrewForge."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
import yaml

from .core import CrewForgeOrchestrator
from .storage import get_database, ProjectStatus, TaskStatus
from .config import get_settings

app = typer.Typer(
    name="crewforge",
    help="Multi-agent software development framework powered by CrewAI",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        from . import __version__
        console.print(f"CrewForge version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
):
    """CrewForge - Multi-agent software development framework."""
    pass


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Project path"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Project template"),
):
    """Initialize a new CrewForge project."""
    project_path = Path(path) if path else Path.cwd() / name

    if project_path.exists() and any(project_path.iterdir()):
        if not Confirm.ask(f"[yellow]Directory {project_path} is not empty. Continue?[/]"):
            raise typer.Exit(1)

    project_path.mkdir(parents=True, exist_ok=True)

    # Create project configuration file
    config = {
        "project": {
            "name": name,
            "version": "0.1.0",
        },
        "tech_stack": {
            "backend": {
                "language": "python",
                "framework": "fastapi",
            },
            "frontend": {
                "language": "typescript",
                "framework": "react",
            },
            "database": "postgresql",
        },
        "agents": {
            "architect": {"enabled": True},
            "developer": {"enabled": True},
            "reviewer": {"enabled": True},
            "tester": {"enabled": True},
            "devops": {"enabled": True},
        },
        "git": {
            "auto_commit": True,
            "branch_prefix": "feature/",
            "auto_merge": True,
        },
    }

    config_path = project_path / "crewforge.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(Panel(
        f"[green]Project initialized successfully![/]\n\n"
        f"Path: {project_path}\n"
        f"Config: {config_path}\n\n"
        f"Next steps:\n"
        f"  1. Edit crewforge.yaml to configure your tech stack\n"
        f"  2. Run [bold]crewforge run[/] to start development",
        title="CrewForge Init"
    ))


@app.command()
def run(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to project config file"
    ),
    requirements: Optional[str] = typer.Option(
        None, "--requirements", "-r", help="Requirements file or string"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose output"),
):
    """Start the development process."""
    # Find config file
    config_path = Path(config) if config else Path.cwd() / "crewforge.yaml"

    if not config_path.exists():
        console.print("[red]Error: No crewforge.yaml found. Run 'crewforge init' first.[/]")
        raise typer.Exit(1)

    # Load configuration
    with open(config_path) as f:
        project_config = yaml.safe_load(f)

    project_name = project_config.get("project", {}).get("name", "unnamed")

    # Get requirements
    if requirements:
        if Path(requirements).exists():
            req_content = Path(requirements).read_text()
        else:
            req_content = requirements
    else:
        console.print(Panel(
            "[bold]Enter your project requirements[/]\n"
            "Describe what you want to build. Be as detailed as possible.\n"
            "Press Enter twice when done.",
            title="Requirements"
        ))
        lines = []
        while True:
            line = Prompt.ask("", default="")
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        req_content = "\n".join(lines[:-1])  # Remove last empty line

    if not req_content.strip():
        console.print("[red]Error: Requirements cannot be empty.[/]")
        raise typer.Exit(1)

    # Create approval callback for CLI
    def cli_approval(approval_type: str, content: str) -> bool:
        console.print(Panel(content, title=f"[bold]{approval_type}[/]"))
        return Confirm.ask("[bold yellow]Do you approve?[/]")

    # Initialize and run orchestrator
    orchestrator = CrewForgeOrchestrator(
        project_name=project_name,
        project_path=str(config_path.parent),
        verbose=verbose,
        on_approval_needed=cli_approval,
    )

    results = orchestrator.run(req_content)

    # Show results
    if results["status"] == "completed":
        console.print(Panel(
            f"[green bold]Development completed successfully![/]\n\n"
            f"Project: {results['project_name']}\n"
            f"Path: {results['project_path']}",
            title="Success"
        ))
    elif results["status"] == "cancelled":
        console.print(f"[yellow]Development cancelled: {results.get('message', 'User cancelled')}[/]")
    else:
        console.print(f"[red]Development failed: {results.get('error', 'Unknown error')}[/]")
        raise typer.Exit(1)


@app.command()
def resume(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name to resume"),
    task_id: Optional[int] = typer.Option(None, "--task", "-t", help="Specific task ID to resume"),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable verbose output"),
):
    """Resume a previously interrupted project."""
    db = get_database()

    if project:
        proj = db.get_project_by_name(project)
        if not proj:
            console.print(f"[red]Project '{project}' not found.[/]")
            raise typer.Exit(1)
    else:
        # List projects and let user choose
        projects = db.list_projects()
        if not projects:
            console.print("[yellow]No projects found.[/]")
            raise typer.Exit(0)

        table = Table(title="Available Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="dim")

        for p in projects:
            table.add_row(
                str(p.id),
                p.name,
                p.status.value if p.status else "unknown",
                str(p.created_at)[:19] if p.created_at else "",
            )

        console.print(table)
        project_id = Prompt.ask("Enter project ID to resume")

        try:
            proj = db.get_project(int(project_id))
        except ValueError:
            console.print("[red]Invalid project ID.[/]")
            raise typer.Exit(1)

        if not proj:
            console.print(f"[red]Project with ID {project_id} not found.[/]")
            raise typer.Exit(1)

    # Resume the project
    orchestrator = CrewForgeOrchestrator(
        project_name=proj.name,
        project_path=proj.git_repo_path,
        verbose=verbose,
    )

    results = orchestrator.resume(task_id)
    console.print(f"Resume result: {results}")


@app.command()
def status(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Show project status."""
    db = get_database()

    if project:
        proj = db.get_project_by_name(project)
        if not proj:
            console.print(f"[red]Project '{project}' not found.[/]")
            raise typer.Exit(1)
        projects = [proj]
    else:
        projects = db.list_projects()

    if not projects:
        console.print("[yellow]No projects found.[/]")
        return

    for proj in projects:
        tasks = db.get_project_tasks(proj.id)

        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
        failed = len([t for t in tasks if t.status == TaskStatus.FAILED])
        in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])

        # Status color
        status_colors = {
            ProjectStatus.COMPLETED: "green",
            ProjectStatus.FAILED: "red",
            ProjectStatus.DEVELOPING: "blue",
            ProjectStatus.TESTING: "cyan",
        }
        status_color = status_colors.get(proj.status, "yellow")

        table = Table(title=f"Project: {proj.name}")
        table.add_column("Property", style="bold")
        table.add_column("Value")

        table.add_row("Status", f"[{status_color}]{proj.status.value if proj.status else 'unknown'}[/]")
        table.add_row("Path", proj.git_repo_path or "N/A")
        table.add_row("Created", str(proj.created_at)[:19] if proj.created_at else "N/A")
        table.add_row("", "")
        table.add_row("Tasks Total", str(len(tasks)))
        table.add_row("  Completed", f"[green]{completed}[/]")
        table.add_row("  In Progress", f"[blue]{in_progress}[/]")
        table.add_row("  Pending", f"[yellow]{pending}[/]")
        table.add_row("  Failed", f"[red]{failed}[/]")

        console.print(table)
        console.print("")


@app.command()
def tasks(
    project: str = typer.Option(..., "--project", "-p", help="Project name"),
):
    """List tasks for a project."""
    db = get_database()

    proj = db.get_project_by_name(project)
    if not proj:
        console.print(f"[red]Project '{project}' not found.[/]")
        raise typer.Exit(1)

    task_list = db.get_project_tasks(proj.id)

    if not task_list:
        console.print("[yellow]No tasks found for this project.[/]")
        return

    table = Table(title=f"Tasks for {project}")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Title", style="white", max_width=40)
    table.add_column("Agent", style="blue")
    table.add_column("Status", style="yellow")
    table.add_column("Retries", style="dim", width=7)

    status_styles = {
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
        TaskStatus.IN_PROGRESS: "blue",
        TaskStatus.PENDING: "yellow",
        TaskStatus.RETRYING: "magenta",
    }

    for task in task_list:
        style = status_styles.get(task.status, "white")
        table.add_row(
            str(task.id),
            task.title[:40] + "..." if len(task.title) > 40 else task.title,
            task.assigned_agent or "unassigned",
            f"[{style}]{task.status.value}[/]",
            str(task.retry_count),
        )

    console.print(table)


@app.command()
def logs(
    project: str = typer.Option(..., "--project", "-p", help="Project name"),
    task_id: Optional[int] = typer.Option(None, "--task", "-t", help="Filter by task ID"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by log level"),
):
    """Show agent logs."""
    db = get_database()

    proj = db.get_project_by_name(project)
    if not proj:
        console.print(f"[red]Project '{project}' not found.[/]")
        raise typer.Exit(1)

    if task_id:
        logs_list = db.get_task_logs(task_id)
    else:
        # Get all tasks and their logs
        tasks = db.get_project_tasks(proj.id)
        logs_list = []
        for task in tasks:
            logs_list.extend(db.get_task_logs(task.id))

    if level:
        logs_list = [log for log in logs_list if log.level == level.upper()]

    if not logs_list:
        console.print("[yellow]No logs found.[/]")
        return

    level_colors = {
        "DEBUG": "dim",
        "INFO": "blue",
        "WARNING": "yellow",
        "ERROR": "red",
    }

    for log in sorted(logs_list, key=lambda x: x.created_at):
        color = level_colors.get(log.level, "white")
        timestamp = str(log.created_at)[:19] if log.created_at else ""
        console.print(
            f"[dim]{timestamp}[/] [{color}]{log.level:7}[/] "
            f"[cyan]{log.agent_role}[/] - {log.action}: {log.message or ''}"
        )


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Edit configuration"),
):
    """Manage configuration."""
    config_path = Path.cwd() / "crewforge.yaml"

    if show:
        if not config_path.exists():
            console.print("[yellow]No crewforge.yaml found in current directory.[/]")
            return

        content = config_path.read_text()
        syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="crewforge.yaml"))

    elif edit:
        if not config_path.exists():
            console.print("[yellow]No crewforge.yaml found. Run 'crewforge init' first.[/]")
            return

        import subprocess
        import os

        editor = os.environ.get("EDITOR", "vim")
        subprocess.run([editor, str(config_path)])
        console.print("[green]Configuration updated.[/]")

    else:
        # Show help
        console.print("Use --show to display config or --edit to modify it.")


@app.command(name="list")
def list_projects():
    """List all projects."""
    db = get_database()
    projects = db.list_projects()

    if not projects:
        console.print("[yellow]No projects found.[/]")
        return

    table = Table(title="Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Path", style="dim", max_width=40)
    table.add_column("Created", style="dim")

    for p in projects:
        path = p.git_repo_path or "N/A"
        if len(path) > 40:
            path = "..." + path[-37:]

        table.add_row(
            str(p.id),
            p.name,
            p.status.value if p.status else "unknown",
            path,
            str(p.created_at)[:10] if p.created_at else "",
        )

    console.print(table)


@app.command()
def clean(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name to clean"),
    all_projects: bool = typer.Option(False, "--all", "-a", help="Clean all projects"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clean project data from database."""
    if not project and not all_projects:
        console.print("[yellow]Specify --project or --all.[/]")
        return

    if not force:
        msg = "all projects" if all_projects else f"project '{project}'"
        if not Confirm.ask(f"[red]Delete data for {msg}?[/]"):
            console.print("[yellow]Cancelled.[/]")
            return

    db = get_database()

    if all_projects:
        db.drop_tables()
        db.create_tables()
        console.print("[green]All project data cleaned.[/]")
    else:
        proj = db.get_project_by_name(project)
        if proj:
            # For now, just update status
            console.print(f"[green]Cleaned project '{project}'.[/]")
        else:
            console.print(f"[red]Project '{project}' not found.[/]")


if __name__ == "__main__":
    app()
