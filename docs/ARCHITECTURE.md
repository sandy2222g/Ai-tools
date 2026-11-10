# Architecture

## Goals

1. **Safe by default.** Code and URLs chosen by a model must not reach the host, the network,
   or secrets unless an operator explicitly allows it.
2. **Fail visibly.** When a weaker control is used, the result says so. Nothing degrades silently.
3. **Dependency-light.** Core tools use the standard library only, which keeps the audit surface small.
4. **Schema-first.** Every tool ships a JSON schema that LLM APIs can consume directly.

## Layout

```
tools/
├── _common/
│   ├── isolation.py    Execution backends (docker | process) and selection logic
│   └── net.py          SSRF-safe HTTP guard (validate_public_url, safe_get)
├── run_code/           Run Python snippets        → isolation.run_isolated
├── run_tests/          Run pytest on a sandbox file → isolation.run_isolated
├── file_tools/         Sandboxed read / write / list
├── organizer_tools/    Sandboxed move / rename / mkdir / info
└── research_tools/     Web search + page fetch    → net.safe_get
```

## Execution path

```
LLM tool call
   │
   ▼
run_code(code, timeout)                       ← schema exposes only code and timeout
   │  creates a fresh temp workdir
   ▼
isolation.run_isolated(["-I", "-"], stdin=code)
   │
   ├─ resolve_backend()  AI_TOOLS_ISOLATION = auto | docker | process
   │      docker ready?  (daemon up AND sandbox image present)
   │
   ├─ docker:  docker run --rm --network none --read-only --cap-drop ALL
   │           --security-opt no-new-privileges --user <non-root>
   │           --memory 256m --cpus 1 --pids-limit 128
   │           --tmpfs /tmp (noexec) --volume <workdir>:/work  <image> python -I -
   │           on timeout: docker rm -f <container>
   │
   └─ process: python -I -   with scrubbed env, RLIMIT_CPU, RLIMIT_AS, RLIMIT_CORE=0
   │
   ▼
{stdout, stderr, exit_code, timed_out, isolation, warning}
```

## Decisions and their rationale

| Decision | Rationale |
|----------|-----------|
| Docker is the default when available | Process-level isolation cannot stop filesystem or network access by model-written code. |
| `auto` falls back to `process` with a warning | Keeps local development working. Production should set `AI_TOOLS_ISOLATION=docker` to fail closed. |
| `isolation` is not in the LLM schema | A model must not be able to request a weaker sandbox. |
| Code is passed over stdin | No host file is written, and there is no path for the code to race with. |
| Only the workdir is mounted | The sandbox sees nothing from the host except the one directory it is allowed to use. |
| Container runs as the invoking user (or `nobody` under root) | Avoids root inside the container, and host-owned files are not written as root. |
| Component-wise path checks (`Path.is_relative_to`) | String-prefix checks accept `sandbox_evil` for `sandbox`. This was a real bypass, fixed in 1.0.0. |
| `safe_get` re-validates each redirect | Otherwise a public URL can redirect to the cloud metadata service (SSRF). |

## Known limitations

- The `process` backend is not a security boundary.
- `safe_get` validates DNS results before connecting. A DNS-rebinding attack that changes the
  record between check and connect is not fully prevented. Enforce egress allowlists at the network layer.
- Docker isolation depends on the container runtime. Use a hardened runtime (gVisor, Kata, or
  a rootless daemon) for multi-tenant deployments.
- Docker-backend tests require a Docker daemon. CI runs them in a dedicated job.

## Testing strategy

| Layer | Where | Needs Docker |
|-------|-------|--------------|
| Security configuration (argv flags) | `tests/test_isolation.py` | No |
| Path confinement regressions | `tests/test_file_tools_security.py`, `tests/test_organizer_tools.py` | No |
| SSRF guard | `tests/test_net_guard.py` | No |
| Process backend behaviour | `tests/test_run_code.py` | No |
| Live container isolation (network, read-only FS, env, timeout) | `tests/test_docker_integration.py` (`-m docker`) | Yes |
