"""LLM configuration with tiered model support."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class AgentRole(str, Enum):
    """Agent roles for LLM tier assignment."""

    MANAGER = "manager"
    ARCHITECT = "architect"
    REVIEWER = "reviewer"
    DEVELOPER = "developer"
    TESTER = "tester"
    DEVOPS = "devops"


class TierConfig(BaseModel):
    """Configuration for a model tier."""

    model: str
    roles: list[AgentRole]


class LLMConfig(BaseSettings):
    """LLM configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="CREWFORGE_LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Provider settings
    provider: LLMProvider = LLMProvider.OPENAI

    # API Keys
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # OpenAI Compatible settings
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"

    # Strategic tier (Manager, Architect, Reviewer)
    strategic_model: str = "gpt-4o"

    # Execution tier (Developer, Tester, DevOps)
    execution_model: str = "gpt-4o-mini"

    # Fallback settings
    fallback_enabled: bool = False
    fallback_provider: LLMProvider = LLMProvider.OLLAMA
    fallback_model: str = "codellama:34b"

    # Model parameters
    temperature: float = 0.7
    max_tokens: int = 4096

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get the appropriate model for a given agent role."""
        strategic_roles = {AgentRole.MANAGER, AgentRole.ARCHITECT, AgentRole.REVIEWER}
        if role in strategic_roles:
            return self.strategic_model
        return self.execution_model

    def get_provider_config(self) -> dict:
        """Get provider-specific configuration."""
        if self.provider == LLMProvider.OPENAI:
            return {
                "api_key": self.openai_api_key,
            }
        elif self.provider == LLMProvider.ANTHROPIC:
            return {
                "api_key": self.anthropic_api_key,
            }
        elif self.provider == LLMProvider.OLLAMA:
            return {
                "base_url": self.ollama_base_url,
            }
        elif self.provider == LLMProvider.OPENAI_COMPATIBLE:
            return {
                "base_url": self.openai_compatible_base_url,
                "api_key": self.openai_compatible_api_key,
            }
        return {}


@lru_cache
def get_llm_config() -> LLMConfig:
    """Get cached LLM configuration."""
    return LLMConfig()
