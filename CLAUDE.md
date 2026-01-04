# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CrewForge is a multi-agent software development framework built on CrewAI. It orchestrates AI agents (Manager, Architect, Developer, Reviewer, Tester, DevOps) to collaboratively develop software projects through a phased workflow with human approval gates. The framework integrates OpenSpec for spec-driven development (SDD), ensuring alignment between requirements and implementation.

## Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_tools.py -v

# Run with coverage
pytest --cov=crewforge

# Lint code
ruff check crewforge/

# Format code
ruff format crewforge/

# Run the CLI
crewforge --help

# Test a workflow locally
crewforge init test-project
cd test-project
crewforge run
```

## Architecture

### Workflow Orchestration

The system uses a phased approach managed by `CrewForgeOrchestrator` (crewforge/core/crew.py:27):

1. **Requirements Confirmation** (Draft Phase) - User approval required (configurable via `require_requirement_approval`)
2. **Architecture Design** (Review Phase) - Architect agent creates OpenSpec documentation (SPEC.md and PLAN.md), recommends tech stack, user approval required
3. **Task Breakdown** - Manager agent creates structured tasks from requirements and OpenSpec
4. **Implementation** (Implement Phase) - Hierarchical process with Manager delegating to Developer/Reviewer, following OpenSpec specifications
5. **Testing** - Tester agent runs unit, integration, and E2E tests based on SPEC.md acceptance criteria
6. **Finalization** (Archive Phase) - Git merge, OpenSpec docs preserved as living documentation

### OpenSpec Integration

The framework follows spec-driven development (SDD) using OpenSpec format:

**OpenSpec Lifecycle**:
- **Draft**: Requirements gathered and confirmed with user
- **Review**: Architect creates SPEC.md (functional requirements) and PLAN.md (architecture)
- **Implement**: Developers build features following OpenSpec specifications
- **Archive**: OpenSpec docs preserved in `.openspec/` directory as living documentation

**OpenSpec Files** (stored in `.openspec/` directory):
- **SPEC.md**: Captures "what" to build - functional requirements, scope, acceptance criteria, use cases
- **PLAN.md**: Captures "how" to build - architecture, tech stack, data models, API design, file structure

**Key Benefits**:
- Alignment between human and AI on requirements before coding
- Living documentation that evolves with the codebase
- Traceability from implementation back to original specifications
- Reduced rework from misunderstandings
- Better onboarding for new developers

### Agent System

All agents inherit from `BaseCrewForgeAgent` (crewforge/core/agents/base.py:13) which provides:
- LLM configuration with provider-specific handling (OpenAI, Anthropic, Ollama, OpenAI-compatible)
- Tool initialization
- Standard agent creation interface

**Hierarchical Delegation**: Manager agent uses `Process.hierarchical` mode where it cannot have tools and delegates to worker agents. For hierarchical mode, create manager with `as_manager=True` (crewforge/core/manager.py:138).

**Model Tiering** (crewforge/config/llm.py:82):
- Strategic tier (Manager, Architect, Reviewer): Uses `strategic_model` (default: gpt-4o)
- Execution tier (Developer, Tester, DevOps): Uses `execution_model` (default: gpt-4o-mini)

### LLM Provider Support

The framework supports multiple LLM providers with flexible configuration (crewforge/config/llm.py):

**OpenAI** - Direct or with custom base_url for proxies:
```python
# When openai_base_url is set, forces openai/ prefix to prevent auto-detection issues
if llm_config.openai_base_url:
    return LLM(model=f"openai/{model}", base_url=..., api_key=...)
```

**Anthropic** - Direct or with custom base_url for proxies:
```python
# No anthropic/ prefix when using custom base_url (proxy handles routing)
if llm_config.anthropic_base_url:
    return LLM(model=model, base_url=..., api_key=...)
```

**OpenAI-compatible** - For third-party APIs (Deepseek, Azure, OpenRouter):
```python
# OpenRouter detection: adds openrouter/ prefix if URL contains "openrouter"
if "openrouter" in base_url:
    return f"openrouter/{model}"
```

### State Persistence

SQLAlchemy models in `crewforge/storage/models.py`:
- **Project**: Stores requirements, architecture, approval status, git info, tech_stack config
- **Task**: Individual tasks with assigned_agent, status, retry_count, parent_task_id for subtasks
- **AgentLog**: Detailed logs of agent actions
- **FileChange**: Tracks file modifications (content_before/after for rollback)

**Status Enums**:
- ProjectStatus: REQUIREMENTS_PENDING → REQUIREMENTS_APPROVED → ARCHITECTURE_PENDING → ARCHITECTURE_APPROVED → DEVELOPING → TESTING → COMPLETED/FAILED
- TaskStatus: PENDING → IN_PROGRESS → COMPLETED/FAILED/RETRYING

### Error Handling

Task failure flow (max 3 retries by default):
1. Task fails, retry_count incremented
2. Manager analyzes failure via `create_failure_handling_prompt()` (crewforge/core/manager.py:214)
3. Manager decides: retry with different approach, reassign to different agent, break down further, or identify requirement issues
4. After `max_retries`, task marked as FAILED

## Common Development Tasks

### Adding a New Agent

1. Create `crewforge/core/agents/new_agent.py`:
```python
from .base import BaseCrewForgeAgent
from ...config import AgentRole

class NewAgent(BaseCrewForgeAgent):
    role = AgentRole.NEW_ROLE  # Add to AgentRole enum first
    name = "Agent Name"
    goal = "What this agent aims to achieve"
    backstory = "Agent's background and expertise"

    def get_tools(self) -> list:
        return self.get_base_tools()  # FileSystem + Shell by default
```

2. Add role to `AgentRole` enum in `crewforge/config/llm.py:20`
3. Register in `crewforge/core/agents/__init__.py`
4. Add to model tier assignment in `llm.py:get_model_for_role()` if needed

### Adding a New Tool

1. Create tool class inheriting from `crewai.tools.BaseTool`
2. Define `name`, `description`, `args_schema` (Pydantic model)
3. Implement `_run()` method with core logic
4. Add to tool collection in `crewforge/tools/` and export
5. Add to agent's `get_tools()` method

### Working with OpenSpec

**Reading OpenSpec Documentation**:
```python
from crewforge.tools import OpenSpecReaderTool

reader = OpenSpecReaderTool()
# Read all OpenSpec docs
all_docs = reader._run(project_path="/path/to/project")
# Read only SPEC.md
spec = reader._run(project_path="/path/to/project", file_type="spec")
```

**Writing OpenSpec Documentation**:
```python
from crewforge.tools import OpenSpecWriterTool

writer = OpenSpecWriterTool()
# Write SPEC.md
writer._run(
    file_type="spec",
    content="# SPEC\n\n## Purpose\n...",
    project_path="/path/to/project"
)
# Write PLAN.md
writer._run(
    file_type="plan",
    content="# PLAN\n\n## Architecture\n...",
    project_path="/path/to/project"
)
```

**Updating OpenSpec Sections**:
```python
from crewforge.tools import OpenSpecUpdateTool

updater = OpenSpecUpdateTool()
updater._run(
    project_path="/path/to/project",
    file_type="plan",
    section="API Design",
    content="Updated API design based on implementation..."
)
```

**OpenSpec Location**: All OpenSpec files are stored in `.openspec/` directory within the project.

### Adding a CLI Command

```python
@app.command()
def new_command(
    arg: str = typer.Argument(..., help="Description"),
    option: bool = typer.Option(False, "--flag", "-f", help="Description"),
):
    """Command description shown in help."""
    # Implementation
```

Use `typer.Argument` for positional args, `typer.Option` for flags.

## Configuration

### Environment Variables

All settings use `CREWFORGE_` prefix (crewforge/config/settings.py):
- `CREWFORGE_LLM_PROVIDER`: openai | anthropic | ollama | openai_compatible
- `CREWFORGE_LLM_STRATEGIC_MODEL`: Model for Manager/Architect/Reviewer
- `CREWFORGE_LLM_EXECUTION_MODEL`: Model for Developer/Tester/DevOps
- `CREWFORGE_DATABASE_URL`: Default sqlite:///crewforge.db
- `CREWFORGE_MAX_RETRIES`: Default 3
- `CREWFORGE_REQUIRE_REQUIREMENT_APPROVAL`: Default true
- `CREWFORGE_REQUIRE_ARCHITECTURE_APPROVAL`: Default true
- `CREWFORGE_OPENSPEC_ENABLED`: Enable OpenSpec integration (default true)
- `CREWFORGE_OPENSPEC_DIR`: OpenSpec directory name (default ".openspec")
- `CREWFORGE_OPENSPEC_AUTO_UPDATE`: Auto-update specs when implementation deviates (default true)

API keys can be set directly:
- `OPENAI_API_KEY` + `OPENAI_BASE_URL` (optional)
- `ANTHROPIC_API_KEY` + `ANTHROPIC_BASE_URL` (optional)
- `CREWFORGE_LLM_OPENAI_COMPATIBLE_BASE_URL` + `CREWFORGE_LLM_OPENAI_COMPATIBLE_API_KEY`

### Tech Stack Auto-Configuration

Tech stack is NOT configured manually. Workflow:
1. User provides requirements
2. Architect agent analyzes and recommends tech stack in YAML format
3. User approves architecture
4. Orchestrator extracts tech_stack from architecture document via regex (crewforge/core/crew.py:273)
5. Tech stack saved to `crewforge.yaml` automatically

Supported project types: frontend-only, backend-only, fullstack, cli, library, other

## Key Implementation Details

### Hierarchical vs Sequential Process

**Hierarchical** (for implementation phase):
```python
crew = Crew(
    agents=[developer, reviewer],  # Worker agents only
    tasks=[...],
    process=Process.hierarchical,
    manager_agent=manager.create_agent(as_manager=True),  # No tools!
)
```

**Sequential** (for architecture, testing phases):
```python
crew = Crew(
    agents=[architect],
    tasks=[task],
    process=Process.sequential,
)
```

### LLM Provider Prefix Handling

The `get_model_for_role()` method (llm.py:82) handles provider prefixes:
- Returns model with provider prefix for LiteLLM routing
- Skips prefix when custom base_url is used (proxy/gateway handles routing)
- Special handling for OpenRouter detection based on URL

### Database Session Management

Use `get_database()` for database operations (crewforge/storage/database.py). It provides methods like:
- `create_project()`, `get_project()`, `get_project_by_name()`
- `create_task()`, `update_task_status()`, `increment_task_retry()`
- `get_project_tasks()`, `get_pending_tasks()`
- `create_agent_log()`, `get_task_logs()`
