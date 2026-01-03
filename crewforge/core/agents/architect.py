"""Architect agent for system design and technical decisions."""

from crewai import Agent

from ...config import AgentRole
from ...tools import FileSystemTool, ShellExecutorTool, WebSearchTool
from .base import BaseCrewForgeAgent


class ArchitectAgent(BaseCrewForgeAgent):
    """Architect agent responsible for system design and technical architecture."""

    role = AgentRole.ARCHITECT
    name = "Software Architect"
    goal = """Design robust, scalable, and maintainable software architectures.
    Make informed technical decisions about technology stack, design patterns,
    and system structure. Create clear architectural documentation and guidelines."""

    backstory = """You are a seasoned software architect with 15+ years of experience
    across multiple technology domains. You have designed systems ranging from
    small microservices to large-scale distributed platforms. You deeply understand
    design patterns, SOLID principles, and modern architectural paradigms including
    microservices, event-driven architecture, and domain-driven design.

    You are technology-agnostic and can work with any programming language or
    framework. You always consider:
    - Scalability and performance requirements
    - Maintainability and code organization
    - Security best practices
    - Developer experience and productivity
    - Cost and infrastructure implications

    You produce clear, actionable architectural documents that developers can follow."""

    def get_tools(self) -> list:
        """Get architect-specific tools."""
        tools = self.get_base_tools()
        tools.append(WebSearchTool())
        return tools

    def create_agent(self) -> Agent:
        """Create the architect agent with specific configuration."""
        if self._agent is None:
            self._agent = Agent(
                role=self.name,
                goal=self.goal,
                backstory=self.backstory,
                tools=self.get_tools(),
                verbose=self.verbose,
                allow_delegation=False,
                llm=self.get_llm(),
                max_iter=10,
            )
        return self._agent
