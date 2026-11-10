# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0]

### Security
- **Fixed path-traversal bypass** in `file_tools`, `run_tests`, `organizer_tools`, and
  `debug_agent`. The previous check used string-prefix matching, so a path such as
  `../sandbox_evil/x` escaped a sandbox named `sandbox`. All checks now compare path
  components (`Path.is_relative_to` / `os.path.commonpath`).
- Added regression tests for sibling-prefix escapes, symlink escapes, and traversal variants.

### Added
- `pyproject.toml` packaging with optional `research`, `agents`, and `dev` extras.
- Pytest suite under `tests/` (run with `make test`).
- GitHub Actions CI: lint, tests on Python 3.10–3.13, dependency audit, and build.
- `Dockerfile` running as a non-root user; `Makefile` for common tasks.
- `SECURITY.md` (threat model and hardening checklist), `CONTRIBUTING.md`, this changelog.

### Changed
- Lint configuration (ruff) enforced in CI; code cleaned to pass it.
