#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from pprint import pformat

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "src" / "dual_agents_workflow" / "cli.py"
TEMPLATE_DIR = ROOT / "src" / "dual_agents_workflow" / "templates"
DIST_DIR = ROOT / "dist"
DIST_FILE = DIST_DIR / "dual-agents-workflow.py"


def standalone_source(templates: dict[str, str]) -> str:
    source = SOURCE_FILE.read_text(encoding="utf-8")
    source = source.replace(
        'TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"',
        "TEMPLATES = __TEMPLATES__",
    )

    start = source.index("def iter_templates() -> list[tuple[str, str]]:")
    end = source.index("\n\ndef is_ignored_scan_path", start)
    replacement = '''def iter_templates() -> list[tuple[str, str]]:
    return sorted(TEMPLATES.items())
'''
    source = source[:start] + replacement + source[end:]
    return source.replace("__TEMPLATES__", pformat(templates, width=100))


def main() -> int:
    templates: dict[str, str] = {}
    for p in sorted(TEMPLATE_DIR.rglob("*")):
        if p.is_file():
            templates[p.relative_to(TEMPLATE_DIR).as_posix()] = p.read_text(encoding="utf-8")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    DIST_FILE.write_text(standalone_source(templates), encoding="utf-8", newline="\n")
    DIST_FILE.chmod(0o755)
    print(f"Wrote {DIST_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
