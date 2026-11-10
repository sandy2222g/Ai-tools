## Summary

<!-- What changed and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature or tool
- [ ] Security fix
- [ ] Refactor / docs / CI

## Checklist

- [ ] `make lint` and `make test` pass locally
- [ ] Tests added or updated, including a security regression test where relevant
- [ ] Filesystem paths are confined with `Path.is_relative_to` (no string-prefix checks)
- [ ] Code execution goes through `tools._common.isolation`; no direct `subprocess` calls on model input
- [ ] Outbound HTTP goes through `tools._common.net.safe_get`
- [ ] `CHANGELOG.md` updated under "Unreleased"
- [ ] No secrets, credentials, or personal data in the diff
