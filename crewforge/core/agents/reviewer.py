"""Code reviewer agent for quality assurance."""

from crewai import Agent

from ...config import AgentRole
from ...tools import FileSystemTool, ShellExecutorTool, GitTool
from .base import BaseCrewForgeAgent


class ReviewerAgent(BaseCrewForgeAgent):
    """Code reviewer agent responsible for code quality and standards."""

    role = AgentRole.REVIEWER
    name = "Senior Code Reviewer"
    goal = """Review code for quality, correctness, security, and adherence to
    best practices. Provide constructive feedback and suggestions for improvement.
    Ensure code meets the project's standards before merging."""

    backstory = """You are a meticulous code reviewer with extensive experience
    across multiple languages and paradigms. You have reviewed thousands of pull
    requests and have developed a keen eye for:

    - Code correctness and logic errors
    - Security vulnerabilities (OWASP Top 10, injection attacks, etc.)
    - Performance issues and optimization opportunities
    - Code style and readability
    - Design pattern usage and architectural consistency
    - Test coverage and test quality
    - Documentation completeness

    You provide feedback that is:
    - Specific and actionable
    - Respectful and constructive
    - Prioritized by severity (critical, major, minor, suggestion)
    - Educational, explaining the "why" behind suggestions

    You balance thoroughness with pragmatism, understanding that perfect is
    the enemy of good. You know when to approve code with minor suggestions
    versus when to request changes for critical issues."""

    def get_tools(self) -> list:
        """Get reviewer-specific tools."""
        tools = self.get_base_tools()
        tools.extend(GitTool.get_tools())
        return tools

    def create_agent(self) -> Agent:
        """Create the reviewer agent."""
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

    def generate_review_checklist(self, language: str) -> str:
        """Generate a language-specific review checklist."""
        common_checks = """
        ## Common Review Checklist
        - [ ] Code compiles/runs without errors
        - [ ] No obvious logic errors
        - [ ] Error handling is appropriate
        - [ ] No hardcoded secrets or credentials
        - [ ] Code is readable and well-named
        - [ ] Comments explain "why", not "what"
        - [ ] No unused code or imports
        - [ ] Consistent formatting
        """

        language_checks = {
            "python": """
            ## Python-Specific
            - [ ] Type hints are used appropriately
            - [ ] No mutable default arguments
            - [ ] Context managers for resources
            - [ ] PEP 8 compliance
            """,
            "javascript": """
            ## JavaScript-Specific
            - [ ] No var, use const/let
            - [ ] Async/await used correctly
            - [ ] No console.log in production code
            - [ ] Proper null/undefined handling
            """,
            "go": """
            ## Go-Specific
            - [ ] Errors are handled, not ignored
            - [ ] No goroutine leaks
            - [ ] Proper defer usage
            - [ ] go fmt applied
            """,
            "rust": """
            ## Rust-Specific
            - [ ] No unwrap() in production code
            - [ ] Proper lifetime annotations
            - [ ] cargo clippy passes
            - [ ] Memory safety verified
            """,
        }

        checks = common_checks
        if language.lower() in language_checks:
            checks += language_checks[language.lower()]

        return checks
