"""Tests for the organizer tools' sandbox confinement."""

import importlib
import os

import pytest


@pytest.fixture
def organizer(tmp_path, monkeypatch):
    """Load organizer_tools with its SANDBOX pointed at a temp directory."""
    import tools.organizer_tools.tool as mod

    mod = importlib.reload(mod)
    box = tmp_path / "organizer_sandbox"
    box.mkdir()
    monkeypatch.setattr(mod, "SANDBOX", os.path.realpath(box))
    return mod


def test_sibling_prefix_escape_is_blocked(organizer, tmp_path):
    (tmp_path / "organizer_sandbox_evil").mkdir()
    with pytest.raises(ValueError):
        organizer._safe_path("../organizer_sandbox_evil")


def test_create_folder_and_list(organizer):
    assert organizer.create_folder("docs")["error"] is None
    listing = organizer.list_files(".")
    assert listing["error"] is None
    assert "docs" in str(listing)
