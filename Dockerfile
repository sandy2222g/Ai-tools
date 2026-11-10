# Sandbox image: the minimal runtime in which untrusted code executes.
#
# It contains only the Python interpreter and pytest (for run_tests). It runs as the
# unprivileged "nobody" user and has no network at run time: the host passes
# --network none, so nothing needs to be configured here.
#
#   make docker          # build ai-agent-tools-sandbox:1.0.0
#   AI_TOOLS_ISOLATION=docker python ...   # require this image (fail closed)

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install "pytest==9.2.0" \
 && mkdir -p /work \
 && chown 65534:65534 /work

WORKDIR /work
USER 65534:65534

LABEL org.opencontainers.image.title="ai-agent-tools-sandbox" \
      org.opencontainers.image.description="Isolated Python runtime for AI agent code execution" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="LicenseRef-Proprietary"
