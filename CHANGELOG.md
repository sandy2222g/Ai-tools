# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0]

### Security
- **Container isolation for code execution.** `run_code` and `run_tests` now run in a
  Docker container by default: no network, read-only root filesystem, all capabilities
  dropped, no-new-privileges, non-root user, memory/CPU/PID limits, scrubbed environment,
  and only the working directory mounted. `AI_TOOLS_ISOLATION=docker` fails closed when
  Docker is unavailable. Every result reports `isolation` and, on fallback, `warning`.
- The isolation backend is not exposed in the LLM tool schemas, so a model cannot request a weaker sandbox.
- **SSRF guard for `research_tools`.** `fetch_page` rejects non-http(s) schemes, embedded
  credentials, and any host resolving to private, loopback, link-local, or metadata
  addresses. Redirects are re-validated on every hop (max 3).
- **Fixed path-traversal bypass** in `file_tools`, `run_tests`, `organizer_tools`, and
  `debug_agent`. The previous check used string-prefix matching, so a path such as
  `../sandbox_evil/x` escaped a sandbox named `sandbox`. All checks now compare path
  components (`Path.is_relative_to` / `os.path.commonpath`).
- Added regression tests for sibling-prefix escapes, symlink escapes, and traversal variants.

### Added
- `pyproject.toml` packaging with optional `research`, `agents`, and `dev` extras.
- Pytest suite under `tests/`: unit tests (`make test`) and Docker isolation tests (`make test-docker`).
- Shared `tools/_common` package with the isolation layer and the SSRF guard.
- `Dockerfile` for the hardened sandbox image (non-root, pinned pytest).
- CodeQL (`security-extended`) and Dependabot configuration.
- `docs/ARCHITECTURE.md` (execution path, decisions, limitations, test strategy).
- Proprietary `LICENSE` (evaluation permitted; commercial license required for production).
- Contribution scaffolding: pull request template, bug report template, CODEOWNERS, pre-commit config.
- GitHub Actions CI: lint, tests on Python 3.10–3.13, dependency audit, and build.
- `Makefile` with `help`, `install`, `lint`, `test`, `test-docker`, `audit`, `build`, `docker`, `clean`.
- `SECURITY.md` (threat model and hardening checklist), `CONTRIBUTING.md`, this changelog.

### Changed
- `run_code` passes code over stdin and returns `isolation` and `warning` fields. The temp-file path is removed.
- `run_tests` runs pytest through the isolation layer with a relative test path.
- `run_code` and `run_tests` result dicts gain `isolation` and `warning` keys (additive).
- Lint configuration (ruff) enforced in CI; code cleaned to pass it.
- CI runs a dedicated Docker isolation job (fail-closed) and a `pip-audit --strict` job.
