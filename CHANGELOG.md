# Changelog

## 0.3.0

- Renamed the project to Dual Agents Workflow.
- Added `--adopt-existing` mode for in-progress projects.
- Added adoption audit, adoption plan, and Codex adoption prompt generation.
- Preserved existing `CLAUDE.md`, `AGENTS.md`, and `README.md` context during adoption.
- Updated the standalone release compiler to derive runtime code from the real CLI.

## 0.2.0

- Split hardcoded templates into real editable files under `src/dual_agents_workflow/templates/`.
- Added release compiler for standalone single-file script.
- Added pytest smoke tests.
- Added GitHub Actions CI across macOS, Linux, and Windows.
- Added issue templates and PR template.
- Updated README examples to use Windows-safe `C:/path/to/project` paths.
- Documented Windows Git Bash recommendation for Git hook compatibility.

## 0.1.0

- Initial dual-agent workflow initializer concept.
