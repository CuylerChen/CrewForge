"""DevOps agent for deployment and infrastructure."""

from crewai import Agent

from ...config import AgentRole
from ...tools import FileSystemTool, ShellExecutorTool, GitTool
from .base import BaseCrewForgeAgent


class DevOpsAgent(BaseCrewForgeAgent):
    """DevOps agent responsible for CI/CD and infrastructure."""

    role = AgentRole.DEVOPS
    name = "DevOps Engineer"
    goal = """Set up and maintain CI/CD pipelines, containerization, and
    deployment configurations. Ensure smooth deployment processes and
    infrastructure reliability."""

    backstory = """You are an experienced DevOps engineer with expertise in:
    - CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
    - Containerization (Docker, Podman)
    - Container orchestration (Kubernetes, Docker Compose)
    - Infrastructure as Code (Terraform, Pulumi)
    - Cloud platforms (AWS, GCP, Azure)
    - Monitoring and logging (Prometheus, Grafana, ELK)
    - Security and compliance automation

    You create infrastructure that is:
    - Reproducible and version-controlled
    - Secure by default
    - Observable with proper monitoring
    - Cost-effective and right-sized
    - Documented for team understanding

    You follow the principle of "automate everything" and believe in
    GitOps practices for infrastructure management."""

    def get_tools(self) -> list:
        """Get DevOps-specific tools."""
        tools = self.get_base_tools()
        tools.extend(GitTool.get_tools())
        return tools

    def create_agent(self) -> Agent:
        """Create the DevOps agent."""
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

    def get_dockerfile_template(self, language: str) -> str:
        """Get a Dockerfile template for a specific language."""
        templates = {
            "python": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
            "go": """FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .

EXPOSE 8080
CMD ["./main"]
""",
            "node": """FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["node", "index.js"]
""",
            "rust": """FROM rust:1.74 AS builder

WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/app /usr/local/bin/

EXPOSE 8080
CMD ["app"]
""",
        }

        return templates.get(language.lower(), templates["python"])

    def get_github_actions_template(self, language: str) -> str:
        """Get a GitHub Actions workflow template."""
        templates = {
            "python": """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
""",
            "go": """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      - name: Run tests
        run: go test -v -race -coverprofile=coverage.txt ./...
      - name: Upload coverage
        uses: codecov/codecov-action@v3
""",
            "node": """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test
""",
        }

        return templates.get(language.lower(), templates["python"])
