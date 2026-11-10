# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |

## Reporting a Vulnerability

Do **not** open a public issue for a security problem.

Report it privately to the security owners listed in `.github/CODEOWNERS`. Include:

- A description of the issue and its impact
- Steps or a proof of concept to reproduce it
- The affected version or commit

Targets: acknowledgement within 2 business days, remediation plan within 10 business days,
and a fix in a patch release for high-severity issues.

## Security Model

Tools here run **model-chosen** code, paths, and URLs. Each tool is designed on the
assumption that its input may be adversarial.

| Tool | Control | Strength |
|------|---------|----------|
| `run_code`, `run_tests` | Docker container: no network, read-only FS, no capabilities, non-root, resource limits, only workdir mounted | Strong when Docker is used |
| `run_code`, `run_tests` | `process` fallback: scrubbed env, rlimits, timeout | **Weak. Not a security boundary.** Flagged in every result via `isolation` and `warning`. |
| `file_tools`, `organizer_tools`, `debug_agent` | Paths resolved (symlinks included) and checked component-wise against the sandbox root | Strong for path confinement |
| `research_tools` | `safe_get`: only http/https, no embedded credentials, all resolved addresses must be public, redirects re-checked (max 3) | Blocks SSRF to loopback, private, link-local, and metadata addresses |

Detailed design: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Deployment Requirements

These are the minimum for a production deployment that runs untrusted model output:

1. Set `AI_TOOLS_ISOLATION=docker` so execution fails closed instead of falling back.
2. Build and pin the sandbox image by digest (`make docker`, then reference it through `AI_TOOLS_SANDBOX_IMAGE`).
3. Use a hardened container runtime (gVisor, Kata, or rootless Docker) for multi-tenant hosts.
4. Apply egress allowlists at the network layer for the agent host. `safe_get` is defence in depth, not a replacement.
5. Keep API keys out of tool inputs and out of the sandbox environment. Use a secrets manager on the agent host.
6. Run `make audit` in CI. It is configured to fail on known vulnerabilities.

## Known Limitations

- The `process` backend provides no filesystem or network isolation.
- `safe_get` checks addresses before connecting. DNS rebinding can defeat that check. Network egress rules are the backstop.
- `run_tests` and `run_code` return stdout and stderr to the model. Treat their output as untrusted data.
- Sandboxes have no persistence between calls.

## Verification

- Path-confinement regressions: `tests/test_file_tools_security.py`, `tests/test_organizer_tools.py`
- SSRF guard: `tests/test_net_guard.py`
- Isolation configuration: `tests/test_isolation.py`
- Live container isolation: `tests/test_docker_integration.py`, run in the `docker-isolation` CI job with `AI_TOOLS_ISOLATION=docker`
- Dependencies: `pip-audit --strict` in CI. CodeQL (`security-extended`) runs on every push and pull request.
