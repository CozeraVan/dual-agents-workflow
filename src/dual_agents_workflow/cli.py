#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

EXECUTABLE_PATHS = {
    "scripts/check_progress_docs.py",
    "scripts/git_finalize_check.py",
    "scripts/agent_status.py",
    "scripts/check-progress-docs.sh",
    "scripts/git-finalize-check.sh",
    "scripts/agent-status.sh",
    ".claude/hooks/progress-gate.sh",
    "_git/hooks/pre-commit",
    ".git/hooks/pre-commit",
}

CORE_DOCS = [
    "CLAUDE.md",
    "AGENTS.md",
    "docs/agent/00_PRODUCT_VISION.md",
    "docs/agent/01_CURRENT_STATUS.md",
    "docs/agent/02_LOCKED_REQUIREMENTS.md",
    "docs/agent/03_ROADMAP.md",
    "docs/agent/04_TASK_HANDOFF.md",
    "docs/agent/05_PROGRESS.md",
    "docs/agent/06_DECISION_LOG.md",
    "docs/agent/07_RECOVERY_PROTOCOL.md",
    "docs/agent/08_IMPLEMENTATION_BRIEF.md",
    "docs/agent/09_CODING_HANDOFF.md",
    "docs/agent/10_REVIEW_REPORT.md",
    "docs/agent/11_AGENT_STATE.md",
    "docs/agent/12_AGENT_BOARD.md",
    "docs/agent/13_CHANGE_CONTROL.md",
]

ADOPTION_DOCS = [
    "docs/agent/14_PROJECT_AUDIT.md",
    "docs/agent/15_ADOPTION_PLAN.md",
    "docs/agent/16_CODEX_ADOPTION_PROMPT.md",
]

GIT_HOOK_TEMPLATE = "_git/hooks/pre-commit"
GIT_HOOK_TARGET = ".git/hooks/pre-commit"

IGNORED_SCAN_DIRS = {
    ".agent-backups",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "vendor",
}

TECH_STACK_MARKERS = {
    "package.json": "Node.js / JavaScript / TypeScript",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "package-lock.json": "npm",
    "app.json": "Expo / React Native",
    "expo-env.d.ts": "Expo / React Native",
    "metro.config.js": "React Native Metro",
    "android": "Android / React Native",
    "ios": "iOS / React Native",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "poetry.lock": "Poetry",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
}


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=check)


def git_available() -> bool:
    return shutil.which("git") is not None


def is_git_repository(project: Path) -> bool:
    if not git_available():
        return False
    return run(["git", "rev-parse", "--is-inside-work-tree"], project).returncode == 0


def backup_if_exists(project: Path, rel: str, backup_root: Path) -> None:
    target = project / rel
    if target.exists() or target.is_symlink():
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir() and not target.is_symlink():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(target, dst)
        else:
            shutil.copy2(target, dst)


def render(content: str, project: Path) -> str:
    return content.replace("{{PROJECT_NAME}}", project.name).replace("{PROJECT_NAME}", project.name)


def set_executable_if_needed(target: Path, rel: str) -> None:
    if rel in EXECUTABLE_PATHS:
        try:
            mode = target.stat().st_mode
            target.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass


def write_file(project: Path, rel: str, content: str, backup_root: Path, overwrite_readme: bool = False) -> None:
    target = project / rel
    if rel == "README.md" and target.exists() and not overwrite_readme:
        return
    backup_if_exists(project, rel, backup_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(content, project), encoding="utf-8", newline="\n")
    set_executable_if_needed(target, rel)


def iter_templates() -> list[tuple[str, str]]:
    if not TEMPLATE_DIR.exists():
        raise FileNotFoundError(f"Template directory not found: {TEMPLATE_DIR}")
    items: list[tuple[str, str]] = []
    for p in sorted(TEMPLATE_DIR.rglob("*")):
        if p.is_file():
            rel = p.relative_to(TEMPLATE_DIR).as_posix()
            items.append((rel, p.read_text(encoding="utf-8")))
    return items


def is_ignored_scan_path(path: Path) -> bool:
    return any(part in IGNORED_SCAN_DIRS for part in path.parts)


def project_tree(project: Path, limit: int = 180) -> list[str]:
    entries: list[str] = []
    for p in sorted(project.rglob("*")):
        rel = p.relative_to(project)
        if is_ignored_scan_path(rel):
            continue
        suffix = "/" if p.is_dir() else ""
        entries.append(f"{rel.as_posix()}{suffix}")
        if len(entries) >= limit:
            entries.append("...")
            break
    return entries


def detect_tech_stack(project: Path) -> list[str]:
    detected: list[str] = []
    for marker, label in TECH_STACK_MARKERS.items():
        if (project / marker).exists() and label not in detected:
            detected.append(label)
    return detected or ["Unknown - Codex should infer during adoption audit"]


def git_lines(project: Path, cmd: list[str]) -> list[str]:
    if not is_git_repository(project):
        return ["Not a git repository."]
    cp = run(cmd, project)
    if cp.returncode != 0:
        return [cp.stderr.strip() or "Command failed."]
    return cp.stdout.splitlines() or ["None"]


def copy_existing_context(project: Path, backup_root: Path) -> list[str]:
    copied: list[str] = []
    context_root = project / "docs" / "agent" / "adoption" / "existing_files"
    for rel in ["CLAUDE.md", "AGENTS.md", "README.md"]:
        src = project / rel
        if src.exists() and src.is_file():
            backup_if_exists(project, f"docs/agent/adoption/existing_files/{rel}", backup_root)
            dst = context_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
    return copied


def write_generated_file(project: Path, rel: str, content: str, backup_root: Path) -> None:
    target = project / rel
    backup_if_exists(project, rel, backup_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(content, project), encoding="utf-8", newline="\n")


def adoption_audit_content(project: Path, copied_context: list[str]) -> str:
    stack = "\n".join(f"- {item}" for item in detect_tech_stack(project))
    tree = "\n".join(f"- {item}" for item in project_tree(project))
    status = "\n".join(f"- {line}" for line in git_lines(project, ["git", "status", "--short"]))
    commits = "\n".join(f"- {line}" for line in git_lines(project, ["git", "log", "--oneline", "-8"]))
    copied = "\n".join(f"- `docs/agent/adoption/existing_files/{item}`" for item in copied_context) or "- None detected"
    return f"""# Project Audit

This file is the adoption entry point for an existing project.

## Adoption Mode

`ADOPT_EXISTING_PROJECT`

## Project

`{{PROJECT_NAME}}`

## Purpose

This project already existed before Dual Agents Workflow was installed. Codex must audit the existing codebase and user history before any implementation work begins.

## Detected Technology Stack

{stack}

## Preserved Existing Context

{copied}

## Current Git Status At Adoption

{status}

## Recent Commits At Adoption

{commits}

## Initial File Tree Snapshot

{tree}

## Codex Audit Requirements

Codex must inspect the actual codebase, existing documentation, preserved context files, and user goals, then update:

- `docs/agent/00_PRODUCT_VISION.md`
- `docs/agent/01_CURRENT_STATUS.md`
- `docs/agent/02_LOCKED_REQUIREMENTS.md`
- `docs/agent/03_ROADMAP.md`
- `docs/agent/04_TASK_HANDOFF.md`
- `docs/agent/05_PROGRESS.md`
- `docs/agent/06_DECISION_LOG.md`
- `docs/agent/08_IMPLEMENTATION_BRIEF.md`
- `docs/agent/11_AGENT_STATE.md`
- `docs/agent/12_AGENT_BOARD.md`

## Non-Negotiable Adoption Rule

Do not modify business code during adoption audit unless the user explicitly changes the task from adoption/planning into implementation.
"""


def adoption_plan_content() -> str:
    return """# Adoption Plan

This plan converts an existing in-progress project into the Dual Agents Workflow.

## Phase 1 - Workflow Install

Status: DONE

- Add Codex and Claude Code workflow instructions.
- Add recoverable project memory under `docs/agent/`.
- Preserve existing user/project context where possible.
- Install local validation scripts and Git hook.

## Phase 2 - Codex Audit And Brainstorm

Status: NEXT

Codex should:

- Read `AGENTS.md`, `CLAUDE.md`, and `docs/agent/11_AGENT_STATE.md`.
- Read `docs/agent/12_AGENT_BOARD.md`, `13_CHANGE_CONTROL.md`, and `14_PROJECT_AUDIT.md`.
- Inspect the actual codebase, configuration, tests, and existing documentation.
- Ask the user clarifying questions about product direction, non-goals, and quality bar.
- Fill in product vision, current status, locked requirements, roadmap, and decision log.

## Phase 3 - First Implementation Brief

Status: PENDING

Codex should prepare `docs/agent/08_IMPLEMENTATION_BRIEF.md` only after the audit is complete and the user confirms the direction.

## Phase 4 - Claude Code Implementation

Status: BLOCKED

Claude Code should not start implementation until:

- `docs/agent/08_IMPLEMENTATION_BRIEF.md` is complete.
- `docs/agent/12_AGENT_BOARD.md` assigns the current task to `CLAUDE_CODE`.
- The current phase is `CLAUDE_IMPLEMENTING`.

## Phase 5 - Review, Finalize, Next

Status: PENDING

Codex performs One-Shot Review-Finalize-Next after Claude Code updates the coding handoff.
"""


def adoption_prompt_content() -> str:
    return """# Codex Adoption Prompt

Use this prompt after installing Dual Agents Workflow into an existing project.

```text
请先不要修改业务代码。请读取 AGENTS.md、CLAUDE.md、docs/agent/11_AGENT_STATE.md、docs/agent/12_AGENT_BOARD.md、docs/agent/13_CHANGE_CONTROL.md、docs/agent/14_PROJECT_AUDIT.md 和 docs/agent/15_ADOPTION_PLAN.md。

然后请审计当前已有代码库，包括目录结构、配置、README、测试、已有 CLAUDE.md 备份、Git 状态和最近提交。请与我进行项目 brainstorm，补全项目愿景、当前状态、Locked Requirements、Roadmap、Decision Log、Progress，并准备第一份 Implementation Brief。

在完成 adoption audit 和文档补全之前，不要修改业务代码，不要让 Claude Code 开始 implementation。
```
"""


def adoption_state_content() -> str:
    return """# Agent State

This file is the source of truth for dual-agent workflow recovery.

## Current Task ID

ADOPTION-0001

## Current Phase

CODEX_PLANNING

## Current Owner

USER

## Last Completed Step

Existing project adopted into Dual Agents Workflow.

## Next Required Step

User should ask Codex to perform the adoption audit and brainstorm before any implementation work.

## Active Change Request

None

## Active Implementation Brief

`docs/agent/08_IMPLEMENTATION_BRIEF.md`

## Active Coding Handoff

`docs/agent/09_CODING_HANDOFF.md`

## Active Review Report

`docs/agent/10_REVIEW_REPORT.md`

## Active Agent Board

`docs/agent/12_AGENT_BOARD.md`

## Active Project Audit

`docs/agent/14_PROJECT_AUDIT.md`

## Active Adoption Plan

`docs/agent/15_ADOPTION_PLAN.md`

## Git State

- Current branch: TODO
- Remote: TODO
- Last checkpoint commit: TODO
- Last implementation commit: TODO
- Last review/planning commit: TODO
- Last pushed commit: TODO

## Standing Approval

NONE

## Recovery Instruction

If unsure where to continue:

1. Read this file first.
2. Read `docs/agent/12_AGENT_BOARD.md`.
3. Read `docs/agent/14_PROJECT_AUDIT.md`.
4. Read `docs/agent/15_ADOPTION_PLAN.md`.
5. Inspect the current Git status before modifying anything.

## Adoption Rule

Do not modify business code until Codex completes the adoption audit, updates the planning documents, and prepares the first Implementation Brief.
"""


def adoption_board_content() -> str:
    return """# Agent Board

This file is the current short handoff board between Codex and Claude Code.

## Current Task ID

ADOPTION-0001

## Current Recipient

CODEX

## Message Type

ADOPTION_AUDIT_TO_CODEX

## Sender

SYSTEM

## Short Message

Existing project workflow files are installed. Codex must audit the codebase and complete planning documents before any coding begins.

## Must Read

- `AGENTS.md`
- `CLAUDE.md`
- `docs/agent/11_AGENT_STATE.md`
- `docs/agent/13_CHANGE_CONTROL.md`
- `docs/agent/14_PROJECT_AUDIT.md`
- `docs/agent/15_ADOPTION_PLAN.md`
- `docs/agent/16_CODEX_ADOPTION_PROMPT.md`

## Must Do

1. Inspect the existing codebase and project configuration.
2. Read preserved existing context under `docs/agent/adoption/existing_files/`.
3. Brainstorm with the user.
4. Update project memory docs.
5. Prepare the first Implementation Brief only after user direction is clear.

## Must Not Do

1. Do not modify business code during adoption audit.
2. Do not assign implementation to Claude Code yet.
3. Do not commit or push unless the user explicitly approves.

## Allowed Files During Adoption Audit

- `docs/agent/*`

## Forbidden Files During Adoption Audit

- `src/*`
- `app/*`
- `components/*`
- `screens/*`
- `services/*`
- `lib/*`
- `api/*`
- `server/*`
- `backend/*`
- `package.json`
- `pyproject.toml`
- lockfiles

## Required Validation

```bash
python scripts/check_progress_docs.py
git diff --check
```
"""


def ensure_git(project: Path, backup_root: Path, hook_content: str | None, no_commit: bool) -> None:
    if not git_available():
        print("WARNING: git not found. Files were created, but git initialization was skipped.")
        return

    if not is_git_repository(project):
        cp = run(["git", "init"], project)
        if cp.returncode != 0:
            print("WARNING: git init failed. Git hook and initial commit were skipped.")
            if cp.stderr.strip():
                print(cp.stderr.strip())
            return

    if hook_content is not None:
        write_file(project, GIT_HOOK_TARGET, hook_content, backup_root, overwrite_readme=True)

    # Git hooks are intentionally not added; .git is not versioned.
    add_targets = [
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        "CLAUDE.md",
        "AGENTS.md",
        "README.md",
        "docs/agent",
        ".claude",
        ".agents",
        ".codex",
        "scripts",
    ]
    run(["git", "add", *add_targets], project)

    if no_commit:
        return

    cp = run(["git", "commit", "-m", "chore: initialize dual-agent workflow"], project)
    if cp.returncode != 0:
        print("Initial commit skipped or failed. This is usually fine if user.name/user.email is not configured or there are no changes.")
        if cp.stderr.strip():
            print(cp.stderr.strip())


def initialize(
    project: Path,
    no_git_commit: bool = False,
    overwrite_readme: bool = False,
    adopt_existing: bool = False,
) -> Path:
    project = project.expanduser().resolve()
    if adopt_existing and not project.exists():
        raise FileNotFoundError(f"Existing project directory not found: {project}")
    project.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = project / ".agent-backups" / timestamp

    mode_label = "Adopting existing project into" if adopt_existing else "Initializing"
    print(f"{mode_label} dual-agent workflow for: {project.name}")
    print(f"Project directory: {project}")

    copied_context = copy_existing_context(project, backup_root) if adopt_existing else []

    hook_content: str | None = None
    for rel, content in iter_templates():
        if rel == GIT_HOOK_TEMPLATE:
            hook_content = content
            continue
        write_file(project, rel, content, backup_root, overwrite_readme=overwrite_readme)

    for rel in [
        "docs/agent/change_requests",
        ".claude/skills",
        ".agents/skills",
        ".claude/hooks",
        ".codex",
        "scripts",
    ]:
        (project / rel).mkdir(parents=True, exist_ok=True)

    if adopt_existing:
        write_generated_file(project, "docs/agent/14_PROJECT_AUDIT.md", adoption_audit_content(project, copied_context), backup_root)
        write_generated_file(project, "docs/agent/15_ADOPTION_PLAN.md", adoption_plan_content(), backup_root)
        write_generated_file(project, "docs/agent/16_CODEX_ADOPTION_PROMPT.md", adoption_prompt_content(), backup_root)
        write_generated_file(project, "docs/agent/11_AGENT_STATE.md", adoption_state_content(), backup_root)
        write_generated_file(project, "docs/agent/12_AGENT_BOARD.md", adoption_board_content(), backup_root)

    ensure_git(project, backup_root, hook_content, no_git_commit)

    print("\nDual-agent workflow initialized.")
    print("\nCreated/updated core files:")
    for rel in CORE_DOCS:
        print(f"- {rel}")
    if adopt_existing:
        print("\nCreated/updated adoption files:")
        for rel in ADOPTION_DOCS:
            print(f"- {rel}")

    print("\nShort prompts:")
    print("Claude Code: 请读取 11 和 12，执行当前 Claude Code 任务。")
    print("Codex: 请读取 11 和 12，执行 One-Shot Review-Finalize-Next。")
    print("New idea: 请读取 11 和 12，把以下新 idea 作为 Change Request 分析，不改代码。")
    print("Architecture change: 请进入 Architecture Change Mode，读取 11、12、13，对以下架构变更做影响分析，不改业务代码。")

    print("\nNext recommended prompt for Codex:")
    if adopt_existing:
        print("请先不要修改业务代码。请读取 AGENTS.md、CLAUDE.md、11、12、13、14、15、16，审计当前代码库，和我 brainstorm，补全项目文档，并准备第一份 Implementation Brief。")
    else:
        print("请先不要修改业务代码。请读取 AGENTS.md、11、12、13，和我进行项目 brainstorm，初始化项目目标、架构、todo list，并准备第一份 Implementation Brief。")

    print("\nBackups for overwritten files, if any:")
    print(backup_root)
    return project


def main(argv: list[str] | None = None) -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="Install Dual Agents Workflow into a new or existing project.")
    parser.add_argument("project_dir", nargs="?", default=".", help="Project directory. Defaults to current directory.")
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="Adopt an existing in-progress project and create Codex audit/planning handoff files.",
    )
    parser.add_argument("--no-git-commit", action="store_true", help="Initialize files and git hook, but do not create initial commit.")
    parser.add_argument("--overwrite-readme", action="store_true", help="Overwrite README.md if it already exists. Default preserves it.")
    args = parser.parse_args(argv)

    try:
        initialize(
            Path(args.project_dir),
            no_git_commit=args.no_git_commit,
            overwrite_readme=args.overwrite_readme,
            adopt_existing=args.adopt_existing,
        )
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI reporting
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
