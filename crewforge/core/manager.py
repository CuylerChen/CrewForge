"""Manager agent for task orchestration and delegation."""

import os
from typing import Optional, Any

from crewai import Agent, LLM

from ..config import AgentRole, get_llm_config, LLMProvider
from ..tools import FileSystemTool, ShellExecutorTool


class ManagerAgent:
    """Manager agent responsible for orchestrating the development team.

    The Manager agent:
    - Analyzes requirements and breaks them into tasks
    - Assigns tasks to appropriate agents
    - Monitors progress and handles failures
    - Coordinates between agents
    - Reports status to the user
    """

    role = AgentRole.MANAGER
    name = "Project Manager"
    goal = """Orchestrate the software development team to deliver high-quality
    software on time. Break down requirements into actionable tasks, assign them
    to the right team members, monitor progress, and ensure successful delivery."""

    backstory = """You are an experienced technical project manager with a strong
    software engineering background. You have successfully led multiple software
    projects from inception to delivery.

    Your strengths include:
    - Breaking down complex requirements into clear, actionable tasks
    - Understanding technical complexity and dependencies
    - Matching tasks to team members' strengths
    - Identifying and mitigating risks early
    - Facilitating communication between team members
    - Making quick decisions when issues arise

    You lead with clarity and purpose, always keeping the end goal in sight.
    You trust your team's expertise while providing guidance when needed.

    Your team consists of:
    - Software Architect: For system design and technical decisions
    - Senior Developer: For code implementation
    - Code Reviewer: For quality assurance
    - QA Engineer: For testing
    - DevOps Engineer: For deployment and infrastructure

    You delegate effectively but remain accountable for the project's success."""

    def __init__(
        self,
        project_path: str,
        verbose: bool = False,
        model: Optional[str] = None,
    ):
        """Initialize the Manager agent.

        Args:
            project_path: Path to the project directory
            verbose: Whether to enable verbose output
            model: Override the default model
        """
        self.project_path = project_path
        self.verbose = verbose
        self._model = model
        self._agent: Optional[Agent] = None

    @property
    def model(self) -> str:
        """Get the model for this agent."""
        if self._model:
            return self._model
        llm_config = get_llm_config()
        return llm_config.get_model_for_role(self.role)

    def get_llm(self) -> Any:
        """Get the LLM instance for this agent."""
        llm_config = get_llm_config()
        model = self.model

        if llm_config.provider == LLMProvider.OPENAI_COMPATIBLE:
            api_key = llm_config.openai_compatible_api_key or os.getenv("OPENROUTER_API_KEY")
            base_url = llm_config.openai_compatible_base_url

            return LLM(
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
        elif llm_config.provider == LLMProvider.ANTHROPIC:
            return LLM(
                model=f"anthropic/{model}",
                api_key=llm_config.anthropic_api_key,
            )
        elif llm_config.provider == LLMProvider.OLLAMA:
            return LLM(
                model=f"ollama/{model}",
                base_url=llm_config.ollama_base_url,
            )
        else:
            return LLM(
                model=model,
                api_key=llm_config.openai_api_key,
            )

    def get_tools(self) -> list:
        """Get manager-specific tools."""
        return [
            *FileSystemTool.get_tools(),
            ShellExecutorTool(),
        ]

    def create_agent(self) -> Agent:
        """Create and return the Manager agent."""
        if self._agent is None:
            self._agent = Agent(
                role=self.name,
                goal=self.goal,
                backstory=self.backstory,
                tools=self.get_tools(),
                verbose=self.verbose,
                allow_delegation=True,  # Manager can delegate to other agents
                llm=self.get_llm(),
                max_iter=20,
            )
        return self._agent

    def create_task_breakdown_prompt(self, requirements: str) -> str:
        """Create a prompt for breaking down requirements into tasks."""
        return f"""Analyze the following requirements and break them down into
specific, actionable development tasks:

REQUIREMENTS:
{requirements}

For each task, provide:
1. Task title (clear and concise)
2. Description (detailed enough for a developer to understand)
3. Assigned role (architect/developer/reviewer/tester/devops)
4. Dependencies (which tasks must be completed first)
5. Estimated complexity (low/medium/high)

Group tasks by phase:
- Architecture & Design
- Implementation
- Testing
- Deployment

Format the response as a structured list."""

    def create_progress_check_prompt(self, completed_tasks: list, pending_tasks: list) -> str:
        """Create a prompt for checking project progress."""
        completed_str = "\n".join(f"- {t}" for t in completed_tasks) or "None yet"
        pending_str = "\n".join(f"- {t}" for t in pending_tasks) or "None"

        return f"""Review the current project progress:

COMPLETED TASKS:
{completed_str}

PENDING TASKS:
{pending_str}

Analyze:
1. Are there any blockers or risks?
2. Should task priorities be adjusted?
3. Are there any issues that need immediate attention?
4. What should be the next focus area?

Provide a brief status summary and recommendations."""

    def create_failure_handling_prompt(self, failed_task: str, error: str, retry_count: int) -> str:
        """Create a prompt for handling task failures."""
        return f"""A task has failed and needs attention:

FAILED TASK: {failed_task}
ERROR: {error}
RETRY COUNT: {retry_count}

Analyze the failure and decide:
1. Can this be fixed by the original agent with different approach?
2. Should this be reassigned to a different agent?
3. Are there prerequisite tasks that were missed?
4. Should the task be broken down further?
5. Is there a fundamental issue with the requirements?

Provide a recovery plan with specific next steps."""

    def __repr__(self) -> str:
        return f"<ManagerAgent(model={self.model})>"
