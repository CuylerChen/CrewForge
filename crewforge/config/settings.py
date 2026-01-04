"""Global settings configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_prefix="CREWFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Project settings
    project_dir: Path = Field(default_factory=Path.cwd)
    output_dir: Path = Field(default=Path("output"))

    # Database
    database_url: str = Field(default="sqlite:///crewforge.db")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    verbose: bool = False

    # Git settings
    git_auto_commit: bool = True
    git_branch_prefix: str = "feature/"
    git_auto_merge: bool = True

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    # Human approval settings
    require_requirement_approval: bool = True
    require_architecture_approval: bool = True

    # OpenSpec settings
    openspec_enabled: bool = True
    openspec_dir: str = ".openspec"
    openspec_auto_update: bool = True  # Auto update specs when implementation deviates


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
