IMAGE ?= ai-agent-tools-sandbox:1.0.0

.PHONY: help install lint format test test-docker audit build docker clean

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install:  ## Editable install with dev tools
	pip install -e ".[dev]"

lint:  ## Run ruff
	ruff check tools tests debug_agent

format:  ## Apply ruff formatting
	ruff format tools tests debug_agent

test:  ## Unit tests (no Docker required)
	pytest -m "not docker"
	pytest tools/run_tests/test_tool.py

test-docker: docker  ## Build the sandbox image and run isolation tests against Docker
	AI_TOOLS_ISOLATION=docker pytest -m docker -v

audit:  ## Check installed dependencies for known vulnerabilities
	pip-audit

build:  ## Build sdist and wheel
	python -m build

docker:  ## Build the sandbox image
	docker build -t $(IMAGE) .

clean:  ## Remove build and cache artifacts
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
