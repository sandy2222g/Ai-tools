.PHONY: install lint format test audit build docker clean

install:
	pip install -e ".[dev]"

lint:
	ruff check tools tests debug_agent

format:
	ruff format tools tests debug_agent

test:
	pytest
	pytest tools/run_tests/test_tool.py

audit:
	pip-audit

build:
	python -m build

docker:
	docker build -t ai-agent-tools:latest .

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
