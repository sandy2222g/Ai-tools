# Contributing

## Development Setup

```bash
python -m venv .venv && source .venv/bin/activate
make install          # installs the package in editable mode with dev extras
make test             # runs the full test suite
make lint             # ruff checks
```

## Adding a Tool

1. Create `tools/<name>/` with `__init__.py`, `tool.py`, `tool_schema.json`, and `README.md`.
2. Keep runtime code **stdlib-only** unless the tool is explicitly an optional extra.
3. Every filesystem path must be confined to a sandbox root with a component-wise check
   (`Path.is_relative_to`). Never use string-prefix comparisons.
4. Return plain `dict`s with an `error` key (`None` on success) so agents can branch on results.
5. Add tests under `tests/` covering success, failure, and at least one security case.
6. Document the tool in the root `README.md` catalog.

## Pull Request Checklist

- [ ] `make lint` passes
- [ ] `make test` passes on Python 3.10 through 3.13 (CI enforces this)
- [ ] New behaviour has tests; security-relevant changes have regression tests
- [ ] `CHANGELOG.md` updated under "Unreleased"
- [ ] No secrets, API keys, or personal data in the diff

## Commit Style

Use short imperative subjects, for example `Fix sibling-prefix escape in file_tools`.
