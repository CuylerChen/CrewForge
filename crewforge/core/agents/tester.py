"""Tester agent for test creation and execution."""

from crewai import Agent

from ...config import AgentRole
from ...tools import FileSystemTool, ShellExecutorTool, BrowserTool
from .base import BaseCrewForgeAgent


class TesterAgent(BaseCrewForgeAgent):
    """Tester agent responsible for testing and quality assurance."""

    role = AgentRole.TESTER
    name = "QA Engineer"
    goal = """Create comprehensive test suites and ensure software quality.
    Write unit tests, integration tests, and E2E tests. Identify edge cases
    and ensure proper test coverage. Execute tests and report results clearly."""

    backstory = """You are an experienced QA engineer with expertise in:
    - Test-driven development (TDD) and behavior-driven development (BDD)
    - Unit testing frameworks (pytest, Jest, Go testing, JUnit)
    - Integration testing strategies
    - End-to-end testing with browser automation (Playwright, Selenium)
    - API testing (Postman, httpx, curl)
    - Performance and load testing
    - Test coverage analysis

    You think adversarially about code, always considering:
    - Edge cases and boundary conditions
    - Error paths and failure modes
    - Race conditions and concurrency issues
    - Security testing scenarios
    - User experience flows

    You write tests that are:
    - Clear and self-documenting
    - Independent and isolated
    - Fast and reliable (no flaky tests)
    - Covering both happy paths and error cases
    - Following the AAA pattern (Arrange, Act, Assert)"""

    def get_tools(self) -> list:
        """Get tester-specific tools."""
        tools = self.get_base_tools()
        tools.extend(BrowserTool.get_tools())
        return tools

    def create_agent(self) -> Agent:
        """Create the tester agent."""
        if self._agent is None:
            self._agent = Agent(
                role=self.name,
                goal=self.goal,
                backstory=self.backstory,
                tools=self.get_tools(),
                verbose=self.verbose,
                allow_delegation=False,
                llm=self.model,
                max_iter=15,
            )
        return self._agent

    def get_test_commands(self, language: str) -> dict:
        """Get test commands for a specific language."""
        commands = {
            "python": {
                "run_tests": "pytest -v",
                "run_coverage": "pytest --cov=. --cov-report=html",
                "run_single": "pytest -v {test_file}::{test_name}",
            },
            "javascript": {
                "run_tests": "npm test",
                "run_coverage": "npm test -- --coverage",
                "run_single": "npm test -- {test_file}",
            },
            "typescript": {
                "run_tests": "npm test",
                "run_coverage": "npm test -- --coverage",
                "run_single": "npm test -- {test_file}",
            },
            "go": {
                "run_tests": "go test ./...",
                "run_coverage": "go test -coverprofile=coverage.out ./...",
                "run_single": "go test -v -run {test_name} ./{package}",
            },
            "rust": {
                "run_tests": "cargo test",
                "run_coverage": "cargo tarpaulin",
                "run_single": "cargo test {test_name}",
            },
        }

        return commands.get(language.lower(), {
            "run_tests": "echo 'Unknown language, please specify test command'",
        })


class E2ETestAgent(BaseCrewForgeAgent):
    """Specialized E2E testing agent with browser automation focus."""

    role = AgentRole.TESTER
    name = "E2E Test Engineer"
    goal = """Create and execute end-to-end tests that verify complete user flows.
    Use browser automation to test web applications thoroughly."""

    backstory = """You are an E2E testing specialist with deep expertise in
    browser automation using Playwright. You excel at:
    - Writing reliable, non-flaky E2E tests
    - Testing complex user workflows
    - Visual regression testing
    - Cross-browser compatibility testing
    - Mobile responsive testing
    - Accessibility testing with automated tools

    You create E2E tests that provide confidence in the application's
    user-facing functionality while maintaining fast execution times."""

    def get_tools(self) -> list:
        """Get E2E tester tools."""
        tools = self.get_base_tools()
        tools.extend(BrowserTool.get_tools())
        return tools
