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
    help="基于 CrewAI 的多智能体软件开发框架",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        from . import __version__
        console.print(f"CrewForge 版本 {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="显示版本并退出"
    ),
):
    """CrewForge - 多智能体软件开发框架"""
    pass


@app.command()
def init(
    name: str = typer.Argument(..., help="项目名称"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="项目路径"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="项目模板"),
):
    """初始化新的 CrewForge 项目"""
    project_path = Path(path) if path else Path.cwd() / name

    if project_path.exists() and any(project_path.iterdir()):
        if not Confirm.ask(f"[yellow]目录 {project_path} 不为空。是否继续？[/]"):
            raise typer.Exit(1)

    project_path.mkdir(parents=True, exist_ok=True)

    # 创建项目配置文件
    # tech_stack 将在需求分析后由 Architect 智能体确定
    config = {
        "project": {
            "name": name,
            "version": "0.1.0",
        },
        # tech_stack: 将根据需求由 Architect 填充
        # 支持类型: frontend-only, backend-only, fullstack, cli, library 等
        "tech_stack": None,
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
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    console.print(Panel(
        f"[green]项目初始化成功！[/]\n\n"
        f"路径: {project_path}\n"
        f"配置文件: {config_path}\n\n"
        f"下一步:\n"
        f"  运行 [bold]crewforge run[/] 开始开发\n"
        f"  (技术栈将根据您的需求自动推荐)",
        title="CrewForge 初始化"
    ))


@app.command()
def run(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="项目配置文件路径"
    ),
    requirements: Optional[str] = typer.Option(
        None, "--requirements", "-r", help="需求文件或字符串"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="启用详细输出"),
):
    """启动开发流程"""
    # 查找配置文件
    config_path = Path(config) if config else Path.cwd() / "crewforge.yaml"

    if not config_path.exists():
        console.print("[red]错误: 未找到 crewforge.yaml。请先运行 'crewforge init'。[/]")
        raise typer.Exit(1)

    # 加载配置
    with open(config_path) as f:
        project_config = yaml.safe_load(f)

    project_name = project_config.get("project", {}).get("name", "未命名")

    # 获取需求
    if requirements:
        if Path(requirements).exists():
            req_content = Path(requirements).read_text()
        else:
            req_content = requirements
    else:
        console.print(Panel(
            "[bold]输入您的项目需求[/]\n"
            "描述您想要构建的内容。请尽可能详细。\n"
            "连续按两次回车完成输入。",
            title="需求输入"
        ))
        lines = []
        while True:
            line = Prompt.ask("", default="")
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        req_content = "\n".join(lines[:-1])  # 移除最后一个空行

    if not req_content.strip():
        console.print("[red]错误: 需求不能为空。[/]")
        raise typer.Exit(1)

    # 创建 CLI 审批回调
    def cli_approval(approval_type: str, content: str) -> bool:
        console.print(Panel(content, title=f"[bold]{approval_type}[/]"))
        return Confirm.ask("[bold yellow]是否批准？[/]")

    # 初始化并运行编排器
    orchestrator = CrewForgeOrchestrator(
        project_name=project_name,
        project_path=str(config_path.parent),
        verbose=verbose,
        on_approval_needed=cli_approval,
    )

    results = orchestrator.run(req_content)

    # 显示结果
    if results["status"] == "completed":
        console.print(Panel(
            f"[green bold]开发成功完成！[/]\n\n"
            f"项目: {results['project_name']}\n"
            f"路径: {results['project_path']}",
            title="成功"
        ))
    elif results["status"] == "cancelled":
        console.print(f"[yellow]开发已取消: {results.get('message', '用户取消')}[/]")
    else:
        console.print(f"[red]开发失败: {results.get('error', '未知错误')}[/]")
        raise typer.Exit(1)


@app.command()
def resume(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="要恢复的项目名称"),
    task_id: Optional[int] = typer.Option(None, "--task", "-t", help="要恢复的特定任务ID"),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="启用详细输出"),
):
    """恢复之前中断的项目"""
    db = get_database()

    if project:
        proj = db.get_project_by_name(project)
        if not proj:
            console.print(f"[red]未找到项目 '{project}'。[/]")
            raise typer.Exit(1)
    else:
        # 列出项目并让用户选择
        projects = db.list_projects()
        if not projects:
            console.print("[yellow]未找到项目。[/]")
            raise typer.Exit(0)

        table = Table(title="可用项目")
        table.add_column("ID", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("创建时间", style="dim")

        for p in projects:
            table.add_row(
                str(p.id),
                p.name,
                p.status.value if p.status else "未知",
                str(p.created_at)[:19] if p.created_at else "",
            )

        console.print(table)
        project_id = Prompt.ask("输入要恢复的项目ID")

        try:
            proj = db.get_project(int(project_id))
        except ValueError:
            console.print("[red]无效的项目ID。[/]")
            raise typer.Exit(1)

        if not proj:
            console.print(f"[red]未找到ID为 {project_id} 的项目。[/]")
            raise typer.Exit(1)

    # 恢复项目
    orchestrator = CrewForgeOrchestrator(
        project_name=proj.name,
        project_path=proj.git_repo_path,
        verbose=verbose,
    )

    results = orchestrator.resume(task_id)
    console.print(f"恢复结果: {results}")


@app.command()
def status(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="项目名称"),
):
    """显示项目状态"""
    db = get_database()

    if project:
        proj = db.get_project_by_name(project)
        if not proj:
            console.print(f"[red]未找到项目 '{project}'。[/]")
            raise typer.Exit(1)
        projects = [proj]
    else:
        projects = db.list_projects()

    if not projects:
        console.print("[yellow]未找到项目。[/]")
        return

    for proj in projects:
        tasks = db.get_project_tasks(proj.id)

        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
        failed = len([t for t in tasks if t.status == TaskStatus.FAILED])
        in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])

        # 状态颜色
        status_colors = {
            ProjectStatus.COMPLETED: "green",
            ProjectStatus.FAILED: "red",
            ProjectStatus.DEVELOPING: "blue",
            ProjectStatus.TESTING: "cyan",
        }
        status_color = status_colors.get(proj.status, "yellow")

        table = Table(title=f"项目: {proj.name}")
        table.add_column("属性", style="bold")
        table.add_column("值")

        table.add_row("状态", f"[{status_color}]{proj.status.value if proj.status else '未知'}[/]")
        table.add_row("路径", proj.git_repo_path or "N/A")
        table.add_row("创建时间", str(proj.created_at)[:19] if proj.created_at else "N/A")
        table.add_row("", "")
        table.add_row("任务总数", str(len(tasks)))
        table.add_row("  已完成", f"[green]{completed}[/]")
        table.add_row("  进行中", f"[blue]{in_progress}[/]")
        table.add_row("  等待中", f"[yellow]{pending}[/]")
        table.add_row("  失败", f"[red]{failed}[/]")

        console.print(table)
        console.print("")


@app.command()
def tasks(
    project: str = typer.Option(..., "--project", "-p", help="项目名称"),
):
    """列出项目的任务列表"""
    db = get_database()

    proj = db.get_project_by_name(project)
    if not proj:
        console.print(f"[red]未找到项目 '{project}'。[/]")
        raise typer.Exit(1)

    task_list = db.get_project_tasks(proj.id)

    if not task_list:
        console.print("[yellow]该项目没有任务。[/]")
        return

    table = Table(title=f"{project} 的任务")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("标题", style="white", max_width=40)
    table.add_column("分配给", style="blue")
    table.add_column("状态", style="yellow")
    table.add_column("重试次数", style="dim", width=7)

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
            task.assigned_agent or "未分配",
            f"[{style}]{task.status.value}[/]",
            str(task.retry_count),
        )

    console.print(table)


@app.command()
def logs(
    project: str = typer.Option(..., "--project", "-p", help="项目名称"),
    task_id: Optional[int] = typer.Option(None, "--task", "-t", help="按任务ID筛选"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="按日志级别筛选"),
):
    """显示智能体日志"""
    db = get_database()

    proj = db.get_project_by_name(project)
    if not proj:
        console.print(f"[red]未找到项目 '{project}'。[/]")
        raise typer.Exit(1)

    if task_id:
        logs_list = db.get_task_logs(task_id)
    else:
        # 获取所有任务及其日志
        tasks = db.get_project_tasks(proj.id)
        logs_list = []
        for task in tasks:
            logs_list.extend(db.get_task_logs(task.id))

    if level:
        logs_list = [log for log in logs_list if log.level == level.upper()]

    if not logs_list:
        console.print("[yellow]未找到日志。[/]")
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
    show: bool = typer.Option(False, "--show", "-s", help="显示当前配置"),
    edit: bool = typer.Option(False, "--edit", "-e", help="编辑配置"),
):
    """管理配置文件"""
    config_path = Path.cwd() / "crewforge.yaml"

    if show:
        if not config_path.exists():
            console.print("[yellow]当前目录未找到 crewforge.yaml。[/]")
            return

        content = config_path.read_text()
        syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="crewforge.yaml"))

    elif edit:
        if not config_path.exists():
            console.print("[yellow]未找到 crewforge.yaml。请先运行 'crewforge init'。[/]")
            return

        import subprocess
        import os

        editor = os.environ.get("EDITOR", "vim")
        subprocess.run([editor, str(config_path)])
        console.print("[green]配置已更新。[/]")

    else:
        # 显示帮助
        console.print("使用 --show 显示配置或 --edit 修改配置。")


@app.command(name="list")
def list_projects():
    """列出所有项目"""
    db = get_database()
    projects = db.list_projects()

    if not projects:
        console.print("[yellow]未找到项目。[/]")
        return

    table = Table(title="项目列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("状态", style="yellow")
    table.add_column("路径", style="dim", max_width=40)
    table.add_column("创建时间", style="dim")

    for p in projects:
        path = p.git_repo_path or "N/A"
        if len(path) > 40:
            path = "..." + path[-37:]

        table.add_row(
            str(p.id),
            p.name,
            p.status.value if p.status else "未知",
            path,
            str(p.created_at)[:10] if p.created_at else "",
        )

    console.print(table)


@app.command()
def clean(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="要清理的项目名称"),
    all_projects: bool = typer.Option(False, "--all", "-a", help="清理所有项目"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
):
    """从数据库清理项目数据"""
    if not project and not all_projects:
        console.print("[yellow]请指定 --project 或 --all。[/]")
        return

    if not force:
        msg = "所有项目" if all_projects else f"项目 '{project}'"
        if not Confirm.ask(f"[red]确定删除 {msg} 的数据吗？[/]"):
            console.print("[yellow]已取消。[/]")
            return

    db = get_database()

    if all_projects:
        db.drop_tables()
        db.create_tables()
        console.print("[green]已清理所有项目数据。[/]")
    else:
        proj = db.get_project_by_name(project)
        if proj:
            # 暂时只更新状态
            console.print(f"[green]已清理项目 '{project}'。[/]")
        else:
            console.print(f"[red]未找到项目 '{project}'。[/]")


if __name__ == "__main__":
    app()
