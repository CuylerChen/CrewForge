"""Developer agent for code implementation."""

from crewai import Agent

from ...config import AgentRole
from ...tools import (
    FileSystemTool,
    ShellExecutorTool,
    GitTool,
    WebSearchTool,
    get_openspec_tools,
)
from .base import BaseCrewForgeAgent


class DeveloperAgent(BaseCrewForgeAgent):
    """Developer agent responsible for implementing code following OpenSpec."""

    role = AgentRole.DEVELOPER
    name = "Senior Developer"
    goal = """Write clean, efficient, and well-documented code that follows
    best practices and the OpenSpec architectural guidelines (SPEC.md and PLAN.md).
    Implement features completely with proper error handling, logging, and tests."""

    backstory = """You are an expert full-stack developer proficient in multiple
    programming languages and frameworks. You have extensive experience with:
    - Backend development (Go, Python, Rust, Node.js, Java)
    - Frontend development (React, Vue, Angular, TypeScript)
    - Database design (SQL and NoSQL)
    - API design (REST, GraphQL, gRPC)
    - DevOps practices (Docker, CI/CD)

    You follow spec-driven development (SDD) practices:
    - Always read and understand OpenSpec documentation (SPEC.md and PLAN.md)
    - Implement features according to functional requirements in SPEC.md
    - Follow architecture and design patterns defined in PLAN.md
    - Update OpenSpec docs if implementation reveals necessary changes
    - Ensure acceptance criteria in SPEC.md are met

    You write code that is:
    - Clean and readable with meaningful variable/function names
    - Well-documented with appropriate comments
    - Following the project's coding standards and conventions
    - Properly handling errors and edge cases
    - Secure and free from common vulnerabilities
    - Testable with clear separation of concerns
    - Consistent with OpenSpec specifications

    You always consider the bigger picture while implementing specific features,
    ensuring consistency with the overall architecture and OpenSpec documentation."""

    def get_tools(self) -> list:
        """Get developer-specific tools."""
        tools = self.get_base_tools()
        tools.extend(GitTool.get_tools())
        tools.append(WebSearchTool())
        # Add OpenSpec tools to read and update specifications
        tools.extend(get_openspec_tools())
        return tools

    def create_agent(self) -> Agent:
        """Create the developer agent."""
        if self._agent is None:
            self._agent = Agent(
                role=self.name,
                goal=self.goal,
                backstory=self.backstory,
                tools=self.get_tools(),
                verbose=self.verbose,
                allow_delegation=False,
                llm=self.get_llm(),
                max_iter=15,
            )
        return self._agent


class FrontendDeveloperAgent(BaseCrewForgeAgent):
    """Specialized frontend developer agent."""

    role = AgentRole.DEVELOPER
    name = "Frontend Developer"
    goal = """Create responsive, accessible, and performant user interfaces.
    Implement frontend features with attention to UX, cross-browser compatibility,
    and modern frontend best practices."""

    backstory = """You are a frontend specialist with deep expertise in:
    - Modern JavaScript/TypeScript
    - React, Vue, or Angular frameworks
    - CSS architecture (Tailwind, CSS-in-JS, SCSS)
    - State management (Redux, Zustand, Pinia)
    - Accessibility (WCAG guidelines)
    - Performance optimization
    - Responsive design

    You create UIs that are beautiful, functional, and inclusive."""

    def get_tools(self) -> list:
        """Get frontend developer tools."""
        return self.get_base_tools()


class BackendDeveloperAgent(BaseCrewForgeAgent):
    """Specialized backend developer agent."""

    role = AgentRole.DEVELOPER
    name = "Backend Developer"
    goal = """Build robust, scalable, and secure backend services.
    Implement APIs, business logic, and data persistence with high reliability."""

    backstory = """You are a backend specialist with expertise in:
    - Server-side languages (Go, Python, Rust, Java, Node.js)
    - API design and implementation
    - Database optimization and modeling
    - Caching strategies
    - Message queues and async processing
    - Security best practices
    - Performance profiling and optimization

    You build backends that are fast, secure, and maintainable."""

    def get_tools(self) -> list:
        """Get backend developer tools."""
        tools = self.get_base_tools()
        tools.extend(GitTool.get_tools())
        return tools
