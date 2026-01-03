# CrewForge

基于 CrewAI 的多智能体软件开发框架。通过协调多个 AI 智能体自动完成软件开发任务。

## 特性

- **多智能体协作**: Manager 统一调度，专业智能体各司其职
- **技术栈无关**: 支持任意编程语言和框架
- **层级式工作流**: Manager 自动分配任务，错误自动回退重试
- **人机协作**: 需求确认和架构审批需人工介入，其他流程全自动
- **状态持久化**: SQLite 存储，支持断点续跑
- **Git 集成**: 功能分支开发，自动合并到 main
- **浏览器测试**: 集成 Playwright 进行 E2E 测试

## 安装

确认 Python 版本（很重要）

CrewAI / CrewForge 一般要求 Python ≥ 3.10（推荐 3.10 / 3.11）

python3 --version

如果你有多个 Python：

which python3

```bash
# 克隆项目
git clone <repo-url>
cd CrewForge

# 创建虚拟环境
python3.11 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -e .

# 安装 Playwright 浏览器（用于 E2E 测试）
playwright install chromium
```

## 配置

### 环境变量

创建 `.env` 文件：

```bash
# LLM 配置（选择一个提供商）
# OpenAI
OPENAI_API_KEY=sk-xxx

# 或 Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx

# 或 OpenAI 兼容接口（如 Deepseek）
CREWFORGE_LLM_PROVIDER=openai_compatible
CREWFORGE_LLM_OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com/v1
CREWFORGE_LLM_OPENAI_COMPATIBLE_API_KEY=xxx

# 可选：搜索 API
CREWFORGE_SEARCH_API_KEY=xxx  # Brave Search API
GITHUB_TOKEN=xxx  # GitHub API（提高速率限制）
```

### 模型分层配置

默认配置：
- **战略层** (Manager, Architect, Reviewer): `gpt-4o`
- **执行层** (Developer, Tester, DevOps): `gpt-4o-mini`

可通过环境变量覆盖：

```bash
CREWFORGE_LLM_STRATEGIC_MODEL=claude-sonnet-4-20250514
CREWFORGE_LLM_EXECUTION_MODEL=claude-3-5-haiku
```

## 使用

### 初始化项目

```bash
crewforge init my-project
cd my-project
```

这会创建 `crewforge.yaml` 配置文件：

```yaml
project:
  name: my-project
  version: 0.1.0

tech_stack:
  backend:
    language: python
    framework: fastapi
  frontend:
    language: typescript
    framework: react
  database: postgresql

agents:
  architect:
    enabled: true
  developer:
    enabled: true
  reviewer:
    enabled: true
  tester:
    enabled: true
  devops:
    enabled: true

git:
  auto_commit: true
  branch_prefix: feature/
  auto_merge: true
```

### 启动开发

```bash
# 交互式输入需求
crewforge run

# 或从文件读取需求
crewforge run --requirements requirements.txt

# 详细日志模式
crewforge run --verbose
```

### 工作流程

1. **需求确认** - 输入需求描述，人工确认
2. **架构设计** - Architect 智能体设计系统架构，人工审批
3. **任务拆解** - Manager 将需求拆分为具体任务
4. **代码实现** - Developer 实现功能，Reviewer 审查代码
5. **自动测试** - Tester 执行单元测试和 E2E 测试
6. **合并发布** - 自动合并功能分支到 main

### 断点续跑

```bash
# 查看项目状态
crewforge status

# 恢复中断的项目
crewforge resume --project my-project
```

### 其他命令

```bash
# 列出所有项目
crewforge list

# 查看任务列表
crewforge tasks --project my-project

# 查看日志
crewforge logs --project my-project

# 查看配置
crewforge config --show

# 清理项目数据
crewforge clean --project my-project
```

## 智能体角色

| 角色 | 职责 | 模型层级 |
|------|------|----------|
| **Manager** | 任务分配、进度监控、错误处理 | 战略层 |
| **Architect** | 系统设计、技术选型、架构文档 | 战略层 |
| **Developer** | 代码实现、功能开发 | 执行层 |
| **Reviewer** | 代码审查、质量把控 | 战略层 |
| **Tester** | 测试编写、测试执行、覆盖率 | 执行层 |
| **DevOps** | CI/CD、Docker、部署配置 | 执行层 |

## 工具能力

智能体可使用以下工具：

- **FileSystem**: 读写文件、创建目录
- **Shell**: 执行命令（build、test 等）
- **Git**: 初始化、分支、提交、合并
- **Browser**: Playwright 驱动的浏览器自动化
- **Search**: Web 搜索、代码搜索、文档搜索

## 项目结构

```
CrewForge/
├── crewforge/
│   ├── __init__.py
│   ├── cli.py              # CLI 入口
│   ├── core/
│   │   ├── crew.py         # CrewAI 编排
│   │   ├── manager.py      # Manager 智能体
│   │   └── agents/         # 各角色智能体
│   ├── tools/
│   │   ├── filesystem.py   # 文件操作
│   │   ├── shell.py        # 命令执行
│   │   ├── git.py          # Git 操作
│   │   ├── browser.py      # Playwright
│   │   └── search.py       # 搜索工具
│   ├── storage/
│   │   ├── database.py     # SQLite 管理
│   │   └── models.py       # 数据模型
│   └── config/
│       ├── settings.py     # 全局配置
│       └── llm.py          # LLM 配置
├── pyproject.toml
└── README.md
```

## 错误处理

当任务失败时：

1. Manager 分析失败原因
2. 决定重试策略（最多 3 次）
3. 可能重新分配给其他智能体
4. 持续失败则暂停并通知用户

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check .
```

## 许可证

MIT
