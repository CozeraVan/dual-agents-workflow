# Dual Agents Workflow

[中文说明](README.zh-CN.md) | [Architecture](docs/ARCHITECTURE.md) | [Contributing](CONTRIBUTING.md)

A cross-platform workflow installer for **dual coding-agent projects**.

The user acts as the Product Owner, Codex acts as Planner / Reviewer / Git Finalizer, and Claude Code acts as the Implementer / Fixer. The tool creates a versioned, file-based workflow for brainstorming, long-term memory, task handoff, implementation, review, Git checkpoints, and change control.

It supports two modes:

| Mode | Use when | Result |
|---|---|---|
| Initialize New Project | You are starting a project from scratch | Create the standard dual-agent workflow files |
| Adopt Existing Project | You already have an in-progress codebase | Install the workflow, preserve existing context, generate Codex adoption audit files, and prepare the project for dual-agent development |

## Visual overview

<p align="center">
  <img src="docs/assets/diagram_1_workflow_EN.png" alt="Dual-agent workflow overview" width="820">
</p>

<p align="center">
  <img src="docs/assets/diagram_2_permissions_EN.png" alt="Dual-agent permissions and responsibilities" width="820">
</p>

## Why this exists

AI coding agents are powerful, but long-running projects often fail for very practical reasons:

- conversation context gets lost;
- agents forget the original project goals;
- planning, coding, review, and Git operations get mixed together;
- multiple agents do not know who owns the next step;
- new ideas and architecture changes get mixed into active coding tasks;
- users have to repeatedly write long prompts.

This project turns those moving parts into a reproducible repository workflow.

For existing projects, it also creates an adoption layer so Codex can inspect the current codebase, brainstorm with the user, fill in missing planning docs, and only then hand implementation work to Claude Code.

## Roles

| Role | Actor | Responsibility |
|---|---|---|
| Product Owner | User | Defines goals, approves direction, accepts major changes |
| Planner / Reviewer / Git Finalizer | Codex | Brainstorming, architecture planning, task decomposition, code review, local Git checkpoints, next-task planning |
| Implementer / Fixer | Claude Code | Implements the current brief, fixes required review issues, updates handoff documents |

Core principle:

> Codex thinks and reviews. Claude Code implements. The user decides direction.

## Daily loop

```text
User → Codex
  Codex writes/updates Implementation Brief and Agent Board
      ↓
User → Claude Code
  Claude Code implements the current task and writes Coding Handoff
      ↓
User → Codex
  Codex performs One-Shot Review-Finalize-Next
      ↓
  If review fails: write Required Fixes, hand back to Claude Code, no commit
  If review passes: local commit, no push by default, prepare next Brief + Board
```

## Short prompts

For Claude Code:

```text
请读取 11 和 12，执行当前 Claude Code 任务。
```

For Codex:

```text
请读取 11 和 12，执行 One-Shot Review-Finalize-Next。
```

For a new idea:

```text
请读取 11 和 12，把以下新 idea 作为 Change Request 分析，不改代码。
```

For an architecture change:

```text
请进入 Architecture Change Mode，读取 11、12、13，对以下架构变更做影响分析，不改业务代码。
```

## Generated files

| File | Purpose |
|---|---|
| `AGENTS.md` | Long-term Codex rules: planning, review, Git finalization, One-Shot Review-Finalize-Next |
| `CLAUDE.md` | Long-term Claude Code rules: implementation, fixing, handoff |
| `docs/agent/00_PRODUCT_VISION.md` | Product vision, scope, non-goals |
| `docs/agent/01_CURRENT_STATUS.md` | Current stage, completed work, known gaps |
| `docs/agent/02_LOCKED_REQUIREMENTS.md` | Hard requirements that must not be silently weakened |
| `docs/agent/03_ROADMAP.md` | Milestones and task roadmap |
| `docs/agent/04_TASK_HANDOFF.md` | Current task handoff |
| `docs/agent/05_PROGRESS.md` | Progress tracker |
| `docs/agent/06_DECISION_LOG.md` | Architecture, data, compliance, and workflow decisions |
| `docs/agent/07_RECOVERY_PROTOCOL.md` | Recovery protocol for interrupted sessions |
| `docs/agent/08_IMPLEMENTATION_BRIEF.md` | Codex's implementation instructions for Claude Code |
| `docs/agent/09_CODING_HANDOFF.md` | Claude Code's implementation summary for Codex |
| `docs/agent/10_REVIEW_REPORT.md` | Codex review report with PASS / FAIL and Required Fixes |
| `docs/agent/11_AGENT_STATE.md` | Current task, phase, owner, Git state, recovery entry |
| `docs/agent/12_AGENT_BOARD.md` | Short-term one-turn handoff board between agents |
| `docs/agent/13_CHANGE_CONTROL.md` | New ideas, architecture changes, and workflow/meta changes |
| `docs/agent/14_PROJECT_AUDIT.md` | Existing-project adoption audit, detected stack, file tree, preserved context |
| `docs/agent/15_ADOPTION_PLAN.md` | Staged plan for converting an existing project into the dual-agent workflow |
| `docs/agent/16_CODEX_ADOPTION_PROMPT.md` | Ready-to-use Codex prompt for adoption brainstorm and documentation completion |

## Installation and usage

### Mode 1: Initialize New Project

### macOS / Linux

```bash
python3 dual-agents-workflow.py /path/to/your/project
```

or:

```bash
chmod +x dual-agents-workflow.sh
./dual-agents-workflow.sh /path/to/your/project
```

### Windows PowerShell

Use forward slashes in examples to avoid backslash escaping issues:

```powershell
py -3 .\dual-agents-workflow.py C:/path/to/your/project
```

or:

```powershell
.\dual-agents-workflow.ps1 C:/path/to/your/project
```

Windows users are encouraged to run Git operations from **Git Bash** when possible, so generated pre-commit hooks behave consistently.

### Mode 2: Adopt Existing Project

Use this when the project already exists and may already have code, README files, Claude Code notes, or partial planning.

```bash
python3 dual-agents-workflow.py /path/to/existing/project --adopt-existing --no-git-commit
```

Adoption mode is intentionally conservative:

- it does not modify business code;
- it preserves an existing `README.md` by default;
- it copies existing `CLAUDE.md`, `AGENTS.md`, and `README.md` into `docs/agent/adoption/existing_files/` when present;
- it writes `14_PROJECT_AUDIT.md`, `15_ADOPTION_PLAN.md`, and `16_CODEX_ADOPTION_PROMPT.md`;
- it sets the workflow state so Codex audits and plans before Claude Code starts implementation.

## First prompt after initialization

Ask Codex:

```text
请先不要修改业务代码。请阅读 AGENTS.md、docs/agent/11_AGENT_STATE.md、docs/agent/12_AGENT_BOARD.md 和 docs/agent/13_CHANGE_CONTROL.md，然后与我进行项目 brainstorm，补全项目愿景、当前状态、Locked Requirements、Roadmap，并准备第一份 Implementation Brief。
```

## First prompt after adoption

Ask Codex:

```text
请先不要修改业务代码。请读取 AGENTS.md、CLAUDE.md、docs/agent/11_AGENT_STATE.md、docs/agent/12_AGENT_BOARD.md、docs/agent/13_CHANGE_CONTROL.md、docs/agent/14_PROJECT_AUDIT.md 和 docs/agent/15_ADOPTION_PLAN.md。

然后请审计当前已有代码库，包括目录结构、配置、README、测试、已有 CLAUDE.md 备份、Git 状态和最近提交。请与我进行项目 brainstorm，补全项目愿景、当前状态、Locked Requirements、Roadmap、Decision Log、Progress，并准备第一份 Implementation Brief。

在完成 adoption audit 和文档补全之前，不要修改业务代码，不要让 Claude Code 开始 implementation。
```

## Development architecture

Template files are real files under:

```text
src/dual_agents_workflow/templates/
```

This avoids a giant hardcoded Python dictionary and makes contributions much easier. For single-file distribution, run:

```bash
python scripts/compile_release.py
```

This creates:

```text
dist/dual-agents-workflow.py
```

## Testing

```bash
python -m pip install -e .[dev]
ruff check .
pytest -q
python scripts/compile_release.py
```

## Good fit

- long-running software projects;
- existing vibe-coded projects that need structure before more implementation;
- solo developers using AI coding agents;
- multi-agent coding workflows;
- projects that need recoverable context;
- projects that benefit from separating planning, implementation, review, and Git operations.

## Not ideal for

- one-off scripts;
- disposable experiments;
- users who do not want any project documentation;
- workflows that intentionally avoid planning and review separation.

## Roadmap

- [ ] More project-type templates: Python, React Native, FastAPI, quant research, data engineering;
- [ ] Stronger cross-platform validation scripts;
- [ ] Optional GitHub remote initialization;
- [ ] Better CR numbering and backlog management;
- [ ] Agent Board task-card rendering;
- [ ] Example projects;
- [ ] More automated tests for initializer scripts;
- [ ] Support for more coding agents.

## License

MIT
