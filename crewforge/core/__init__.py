"""Core module for CrewAI orchestration."""

from .crew import CrewForgeOrchestrator
from .manager import ManagerAgent

__all__ = ["CrewForgeOrchestrator", "ManagerAgent"]
