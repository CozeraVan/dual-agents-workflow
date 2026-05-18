# Architecture

This repository intentionally keeps template content as normal files instead of embedding thousands of lines of Markdown into a giant Python dictionary.

## Source Layout

```text
dual-agents-workflow/
├── dual-agents-workflow.py              # repo-friendly wrapper
├── dual-agents-workflow.sh              # macOS/Linux wrapper
├── dual-agents-workflow.ps1             # Windows PowerShell wrapper
├── src/dual_agents_workflow/cli.py      # workflow installer runtime
├── src/dual_agents_workflow/templates/
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── docs/agent/00-13...
│   ├── scripts/...
│   └── .claude / .agents / .codex ...
├── scripts/compile_release.py          # builds dist/dual-agents-workflow.py
└── tests/test_initializer.py
```

## Why templates are real files

Real template files make the project easier to maintain:

- Markdown files get syntax highlighting and preview.
- Diffs are readable.
- Contributors can update one template without editing a huge Python string.
- The release compiler can still produce a single-file standalone script for users who want one file only.

## Runtime modes

Dual Agents Workflow supports two modes:

- Initialize New Project: create the standard workflow files for a new project directory.
- Adopt Existing Project: install the same workflow into an existing codebase, preserve existing context files, and generate adoption audit/planning docs.

## Runtime flow

1. The CLI loads all files under `src/dual_agents_workflow/templates/`.
2. Files are rendered with the target project name.
3. Existing files are backed up under `.agent-backups/<timestamp>/` before overwrite.
4. Git is initialized if needed.
5. A pre-commit hook is written after Git initialization.
6. The generated workflow files are staged and optionally committed.

In adoption mode, the runtime also writes:

- `docs/agent/14_PROJECT_AUDIT.md`
- `docs/agent/15_ADOPTION_PLAN.md`
- `docs/agent/16_CODEX_ADOPTION_PROMPT.md`
- preserved existing context under `docs/agent/adoption/existing_files/`

## Release flow

Run:

```bash
python scripts/compile_release.py
```

This creates:

```text
dist/dual-agents-workflow.py
```

The release script embeds the current templates, so it can be copied and run without the full repository.
