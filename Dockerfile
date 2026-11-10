# Hardened runtime image. The core tools are stdlib-only, so the image stays small.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 agent
COPY pyproject.toml README.md ./
COPY tools ./tools
RUN pip install --no-cache-dir .

USER agent
WORKDIR /home/agent/work

ENTRYPOINT ["python", "-c"]
CMD ["import tools.run_code as r; print(r.run_code('print(1+1)'))"]
