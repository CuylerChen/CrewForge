"""Database models for state persistence."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ProjectStatus(str, Enum):
    """Project status."""

    INITIALIZING = "initializing"
    REQUIREMENTS_PENDING = "requirements_pending"
    REQUIREMENTS_APPROVED = "requirements_approved"
    ARCHITECTURE_PENDING = "architecture_pending"
    ARCHITECTURE_APPROVED = "architecture_approved"
    DEVELOPING = "developing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    """Project model for tracking overall project state."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.INITIALIZING)

    # Configuration
    config = Column(JSON, nullable=True)  # Stores project.yaml content
    tech_stack = Column(JSON, nullable=True)

    # Git info
    git_repo_path = Column(String(512), nullable=True)
    git_main_branch = Column(String(100), default="main")
    current_branch = Column(String(100), nullable=True)

    # Requirements and architecture (for approval flow)
    requirements = Column(Text, nullable=True)
    requirements_approved = Column(Boolean, default=False)
    architecture = Column(Text, nullable=True)
    architecture_approved = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    """Task model for tracking individual tasks."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Task info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(100), nullable=True)  # e.g., "feature", "bugfix", "refactor"

    # Assignment
    assigned_agent = Column(String(100), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)

    # Status
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Git info
    branch_name = Column(String(100), nullable=True)
    commit_hash = Column(String(40), nullable=True)

    # Result
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    logs = relationship("AgentLog", back_populates="task", cascade="all, delete-orphan")


class AgentLog(Base):
    """Log entries for agent actions."""

    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    # Log info
    agent_role = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    # Logging level
    level = Column(String(20), default="INFO")  # DEBUG, INFO, WARNING, ERROR

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="logs")


class FileChange(Base):
    """Track file changes made by agents."""

    __tablename__ = "file_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    # File info
    file_path = Column(String(1024), nullable=False)
    change_type = Column(String(50), nullable=False)  # create, modify, delete
    content_before = Column(Text, nullable=True)
    content_after = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
