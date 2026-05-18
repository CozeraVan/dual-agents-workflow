# Release Checklist

Before publishing a GitHub release:

1. Run tests:

```bash
pytest -q
```

2. Run lint:

```bash
ruff check .
```

3. Compile standalone release script:

```bash
python scripts/compile_release.py
```

4. Smoke test the release script:

```bash
python dist/dual-agents-workflow.py /tmp/dual-agent-smoke --no-git-commit
```

5. Verify docs:

- README.md
- README.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- docs/ARCHITECTURE.md

6. Tag release:

```bash
git tag v0.3.0
git push origin v0.3.0
```
