# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |

## Reporting a Vulnerability

Please do **not** open a public issue for security problems.

Report vulnerabilities privately to the maintainers. Include:

- A description of the issue and its impact
- Steps or a proof of concept to reproduce it
- The affected version or commit

We aim to acknowledge reports within 2 business days and to provide a remediation
plan within 10 business days.

## Security Model

These tools are designed to run **inside a sandbox directory** with no network access
except where explicitly noted (`research_tools`).

| Tool | Controls |
|------|----------|
| `file_tools`, `organizer_tools`, `debug_agent` | All paths are resolved and must stay within the sandbox root (component-wise check; symlinks are resolved first). |
| `run_code` | Runs code in a **separate process** with a hard timeout. It is **not** a security boundary: untrusted code can still access the host. Run agents that execute model-generated code inside a container or VM. |
| `run_tests` | Test files must resolve inside the sandbox. Same process-isolation caveat as `run_code`. |
| `research_tools` | Outbound HTTP(S) to arbitrary URLs. Restrict egress at the network layer if this matters for your deployment. |

## Hardening Checklist for Deployments

- Run agents in a container with a read-only root filesystem and a non-root user
  (see `Dockerfile`).
- Apply network egress allowlists where code execution or web access is enabled.
- Set resource limits (CPU, memory, PIDs) on the container.
- Keep API keys out of source control; use a secrets manager.
- Run `make audit` (pip-audit) in CI and before each release.

## Known Limitations

- `run_code` provides timeouts, not isolation.
- Output truncation is applied to `run_tests` but not to `run_code` stdout.
