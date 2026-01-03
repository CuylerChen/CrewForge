# CLAUDE.md - CrewForge Project Guide

## Project Overview

CrewForge is a multi-agent software development framework built on CrewAI. It orchestrates multiple AI agents to collaboratively develop software projects.

## Architecture

```
CLI (typer) → CrewForgeOrchestrator → CrewAI Crew
                     ↓
              ManagerAgent (hierarchical)
                     ↓
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
Architect      Developer         Tester
    ↓                ↓                ↓
Reviewer          DevOps         Browser
```

## Key Components

### Core (`crewforge/core/`)
- `crew.py`: Main orchestrator, manages workflow phases
- `manager.py`: Manager agent for task delegation
- `agents/`: Individual agent implementations

### Tools (`crewforge/tools/`)
- `filesystem.py`: File read/write operations
- `shell.py`: Command execution
- `git.py`: Git operations (init, commit, branch, merge)
- `browser.py`: Playwright-based browser automation
- `search.py`: Web and code search

### Storage (`crewforge/storage/`)
- `models.py`: SQLAlchemy models (Project, Task, AgentLog)
- `database.py`: Database operations and session management

### Config (`crewforge/config/`)
- `settings.py`: Application settings via pydantic-settings
- `llm.py`: LLM provider and model tier configuration

## Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run the CLI
crewforge --help

# Run tests
pytest -v

# Lint code
ruff check crewforge/

# Format code
ruff format crewforge/
```

## Common Tasks

### Adding a New Agent

1. Create `crewforge/core/agents/new_agent.py`
2. Inherit from `BaseCrewForgeAgent`
3. Define `role`, `name`, `goal`, `backstory`
4. Implement `get_tools()` method
5. Register in `crewforge/core/agents/__init__.py`

### Adding a New Tool

1. Create tool class inheriting from `crewai.tools.BaseTool`
2. Define `name`, `description`, `args_schema`
3. Implement `_run()` method
4. Add to appropriate tool collection in `crewforge/tools/`

### Adding a CLI Command

1. Add command function in `crewforge/cli.py`
2. Use `@app.command()` decorator
3. Use `typer.Option` for flags, `typer.Argument` for positional args

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=crewforge

# Run specific test
pytest tests/test_tools.py -v
```

## Database Schema

- **Project**: Overall project state, requirements, architecture
- **Task**: Individual development tasks with status tracking
- **AgentLog**: Detailed logs of agent actions
- **FileChange**: Track file modifications (for rollback)

## Error Handling

When a task fails:
1. `increment_task_retry()` increases retry count
2. Manager analyzes failure via `create_failure_handling_prompt()`
3. Task reassigned or broken down further
4. After `max_retries`, task marked as failed

## Environment Variables

All settings can be overridden via environment variables with `CREWFORGE_` prefix.
See `.env.example` for full list.
