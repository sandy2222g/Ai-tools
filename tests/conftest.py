"""Shared pytest fixtures. Every test runs against an isolated temporary sandbox."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A fresh, empty sandbox directory unique to each test."""
    root = tmp_path / "sandbox"
    root.mkdir()
    return root
