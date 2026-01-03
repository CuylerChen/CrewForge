"""Database management for state persistence."""

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Project, Task, AgentLog, TaskStatus, ProjectStatus


class Database:
    """Database manager for CrewForge state persistence."""

    def __init__(self, database_url: str = "sqlite:///crewforge.db"):
        """Initialize database connection."""
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Project operations
    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        config: Optional[dict] = None,
        tech_stack: Optional[dict] = None,
        git_repo_path: Optional[str] = None,
    ) -> Project:
        """Create a new project."""
        with self.get_session() as session:
            project = Project(
                name=name,
                description=description,
                config=config,
                tech_stack=tech_stack,
                git_repo_path=git_repo_path,
            )
            session.add(project)
            session.flush()
            session.refresh(project)
            project_id = project.id
        return self.get_project(project_id)

    def get_project(self, project_id: int) -> Optional[Project]:
        """Get a project by ID."""
        with self.get_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                session.expunge(project)
            return project

    def get_project_by_name(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        with self.get_session() as session:
            project = session.query(Project).filter(Project.name == name).first()
            if project:
                session.expunge(project)
            return project

    def update_project_status(self, project_id: int, status: ProjectStatus) -> None:
        """Update project status."""
        with self.get_session() as session:
            session.query(Project).filter(Project.id == project_id).update({"status": status})

    def update_project_requirements(
        self, project_id: int, requirements: str, approved: bool = False
    ) -> None:
        """Update project requirements."""
        with self.get_session() as session:
            session.query(Project).filter(Project.id == project_id).update({
                "requirements": requirements,
                "requirements_approved": approved,
            })

    def update_project_architecture(
        self, project_id: int, architecture: str, approved: bool = False
    ) -> None:
        """Update project architecture."""
        with self.get_session() as session:
            session.query(Project).filter(Project.id == project_id).update({
                "architecture": architecture,
                "architecture_approved": approved,
            })

    def list_projects(self) -> list[Project]:
        """List all projects."""
        with self.get_session() as session:
            projects = session.query(Project).all()
            for p in projects:
                session.expunge(p)
            return projects

    # Task operations
    def create_task(
        self,
        project_id: int,
        title: str,
        description: Optional[str] = None,
        task_type: Optional[str] = None,
        assigned_agent: Optional[str] = None,
        parent_task_id: Optional[int] = None,
    ) -> Task:
        """Create a new task."""
        with self.get_session() as session:
            task = Task(
                project_id=project_id,
                title=title,
                description=description,
                task_type=task_type,
                assigned_agent=assigned_agent,
                parent_task_id=parent_task_id,
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            task_id = task.id
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID."""
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                session.expunge(task)
            return task

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update task status."""
        from datetime import datetime

        updates = {"status": status}
        if status == TaskStatus.IN_PROGRESS:
            updates["started_at"] = datetime.utcnow()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            updates["completed_at"] = datetime.utcnow()
        if result:
            updates["result"] = result
        if error_message:
            updates["error_message"] = error_message

        with self.get_session() as session:
            session.query(Task).filter(Task.id == task_id).update(updates)

    def increment_task_retry(self, task_id: int) -> int:
        """Increment task retry count and return new count."""
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                session.flush()
                return task.retry_count
            return 0

    def get_pending_tasks(self, project_id: int) -> list[Task]:
        """Get all pending tasks for a project."""
        with self.get_session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.project_id == project_id, Task.status == TaskStatus.PENDING)
                .all()
            )
            for t in tasks:
                session.expunge(t)
            return tasks

    def get_project_tasks(self, project_id: int) -> list[Task]:
        """Get all tasks for a project."""
        with self.get_session() as session:
            tasks = session.query(Task).filter(Task.project_id == project_id).all()
            for t in tasks:
                session.expunge(t)
            return tasks

    # Agent log operations
    def add_agent_log(
        self,
        task_id: int,
        agent_role: str,
        action: str,
        message: Optional[str] = None,
        details: Optional[dict] = None,
        level: str = "INFO",
    ) -> AgentLog:
        """Add an agent log entry."""
        with self.get_session() as session:
            log = AgentLog(
                task_id=task_id,
                agent_role=agent_role,
                action=action,
                message=message,
                details=details,
                level=level,
            )
            session.add(log)
            session.flush()
            session.refresh(log)
            log_id = log.id
        return self.get_agent_log(log_id)

    def get_agent_log(self, log_id: int) -> Optional[AgentLog]:
        """Get an agent log by ID."""
        with self.get_session() as session:
            log = session.query(AgentLog).filter(AgentLog.id == log_id).first()
            if log:
                session.expunge(log)
            return log

    def get_task_logs(self, task_id: int) -> list[AgentLog]:
        """Get all logs for a task."""
        with self.get_session() as session:
            logs = session.query(AgentLog).filter(AgentLog.task_id == task_id).all()
            for log in logs:
                session.expunge(log)
            return logs


_database: Optional[Database] = None


def get_database(database_url: Optional[str] = None) -> Database:
    """Get or create database instance."""
    global _database
    if _database is None:
        from ..config import get_settings

        url = database_url or get_settings().database_url
        _database = Database(url)
        _database.create_tables()
    return _database


def reset_database() -> None:
    """Reset the global database instance."""
    global _database
    _database = None
