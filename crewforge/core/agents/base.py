"""Base agent class for all CrewForge agents."""

import os
from abc import ABC, abstractmethod
from typing import Optional, Any

from crewai import Agent, LLM

from ...config import get_llm_config, AgentRole, LLMProvider
from ...tools import FileSystemTool, ShellExecutorTool, GitTool


class BaseCrewForgeAgent(ABC):
    """Base class for all CrewForge agents."""

    role: AgentRole
    name: str
    goal: str
    backstory: str

    def __init__(
        self,
        project_path: str,
        verbose: bool = False,
        model: Optional[str] = None,
    ):
        """Initialize the agent.

        Args:
            project_path: Path to the project directory
            verbose: Whether to enable verbose output
            model: Override the default model for this agent
        """
        self.project_path = project_path
        self.verbose = verbose
        self._model = model
        self._agent: Optional[Agent] = None

    def get_llm(self) -> Any:
        """Get the LLM instance for this agent."""
        llm_config = get_llm_config()

        # get_model_for_role already handles provider prefixes
        if self._model:
            model = self._model
        else:
            model = llm_config.get_model_for_role(self.role)

        # For OpenRouter or other OpenAI-compatible APIs
        if llm_config.provider == LLMProvider.OPENAI_COMPATIBLE:
            api_key = llm_config.openai_compatible_api_key or os.getenv("OPENROUTER_API_KEY")
            base_url = llm_config.openai_compatible_base_url

            return LLM(
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
        elif llm_config.provider == LLMProvider.ANTHROPIC:
            # Support custom base_url for Anthropic proxies
            if llm_config.anthropic_base_url:
                return LLM(
                    model=model,  # No prefix for custom endpoints
                    base_url=llm_config.anthropic_base_url,
                    api_key=llm_config.anthropic_api_key,
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens,
                )
            else:
                return LLM(
                    model=model,  # get_model_for_role adds anthropic/ prefix
                    api_key=llm_config.anthropic_api_key,
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens,
                )
        elif llm_config.provider == LLMProvider.OLLAMA:
            return LLM(
                model=model,  # get_model_for_role adds ollama/ prefix
                base_url=llm_config.ollama_base_url,
            )
        else:
            # OpenAI - support custom base_url
            if llm_config.openai_base_url:
                # Force openai provider to avoid LiteLLM auto-detecting based on model name
                # This prevents it from trying to use anthropic SDK for claude models
                return LLM(
                    model=f"openai/{model}",
                    base_url=llm_config.openai_base_url,
                    api_key=llm_config.openai_api_key,
                )
            else:
                return LLM(
                    model=model,
                    api_key=llm_config.openai_api_key,
                )

    @property
    def model(self) -> str:
        """Get the model name for this agent."""
        if self._model:
            return self._model
        llm_config = get_llm_config()
        return llm_config.get_model_for_role(self.role)

    @abstractmethod
    def get_tools(self) -> list:
        """Get the tools available to this agent."""
        pass

    def get_base_tools(self) -> list:
        """Get base tools available to all agents."""
        return [
            *FileSystemTool.get_tools(),
            ShellExecutorTool(),
        ]

    def create_agent(self) -> Agent:
        """Create and return the CrewAI agent."""
        if self._agent is None:
            self._agent = Agent(
                role=self.name,
                goal=self.goal,
                backstory=self.backstory,
                tools=self.get_tools(),
                verbose=self.verbose,
                allow_delegation=self._allow_delegation(),
                llm=self.get_llm(),
            )
        return self._agent

    def _allow_delegation(self) -> bool:
        """Whether this agent can delegate tasks."""
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(role={self.role.value}, model={self.model})>"
