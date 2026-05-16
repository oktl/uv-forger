"""Tests for app.core.history_manager."""

import json

import pytest

from uv_forger.core.history_manager import (
    MAX_HISTORY_ENTRIES,
    ProjectHistoryEntry,
    add_to_history,
    clear_history,
    load_history,
    make_history_entry,
    save_history,
)


def _make_entry(name: str = "my-project", path: str = "/tmp/projects", **kwargs):
    """Create a test history entry with sensible defaults."""
    defaults = {
        "project_name": name,
        "project_path": path,
        "python_version": "3.14",
        "git_enabled": True,
        "include_starter_files": True,
        "ui_project_enabled": False,
        "framework": None,
        "other_project_enabled": False,
        "project_type": None,
        "folders": ["core", "utils"],
        "packages": ["httpx"],
        "built_at": "2026-02-19T10:00:00+00:00",
    }
    defaults.update(kwargs)
    return ProjectHistoryEntry(**defaults)


@pytest.fixture(autouse=True)
def _use_tmp_history(tmp_path, monkeypatch):
    """Redirect HISTORY_FILE to a temp directory for every test."""
    tmp_file = tmp_path / "recent_projects.json"
    monkeypatch.setattr("uv_forger.core.history_manager.HISTORY_FILE", tmp_file)
    monkeypatch.setattr("uv_forger.core.history_manager.SETTINGS_DIR", tmp_path)


def test_load_empty():
    """Returns empty list when no file exists."""
    assert load_history() == []


def test_save_and_load_roundtrip():
    """Entries survive a save/load cycle."""
    entry = _make_entry()
    save_history([entry])
    loaded = load_history()
    assert len(loaded) == 1
    assert loaded[0].project_name == "my-project"
    assert loaded[0].packages == ["httpx"]


def test_max_entries_cap():
    """Adding more than MAX entries keeps only the most recent."""
    for i in range(MAX_HISTORY_ENTRIES + 2):
        add_to_history(_make_entry(name=f"project-{i}", path=f"/tmp/{i}"))

    entries = load_history()
    assert len(entries) == MAX_HISTORY_ENTRIES
    # Most recent should be first
    assert entries[0].project_name == f"project-{MAX_HISTORY_ENTRIES + 1}"


def test_deduplication():
    """Same name+path replaces old entry at top."""
    add_to_history(_make_entry(name="dup", path="/tmp/p", packages=["old-pkg"]))
    add_to_history(_make_entry(name="other", path="/tmp/other"))
    add_to_history(_make_entry(name="dup", path="/tmp/p", packages=["new-pkg"]))

    entries = load_history()
    assert entries[0].project_name == "dup"
    assert entries[0].packages == ["new-pkg"]
    # Should only have 2 entries, not 3
    dup_count = sum(1 for e in entries if e.project_name == "dup")
    assert dup_count == 1


def test_corrupt_json_returns_empty(tmp_path, monkeypatch):
    """Gracefully returns empty list for corrupt JSON."""
    tmp_file = tmp_path / "recent_projects.json"
    monkeypatch.setattr("uv_forger.core.history_manager.HISTORY_FILE", tmp_file)
    tmp_file.write_text("{not valid json!!!", encoding="utf-8")
    assert load_history() == []


def test_forward_compatible(tmp_path, monkeypatch):
    """Ignores unknown keys in stored JSON."""
    tmp_file = tmp_path / "recent_projects.json"
    monkeypatch.setattr("uv_forger.core.history_manager.HISTORY_FILE", tmp_file)
    data = [
        {
            "project_name": "test",
            "project_path": "/tmp",
            "python_version": "3.14",
            "git_enabled": True,
            "include_starter_files": True,
            "ui_project_enabled": False,
            "framework": None,
            "other_project_enabled": False,
            "project_type": None,
            "folders": [],
            "packages": [],
            "built_at": "2026-02-19T10:00:00+00:00",
            "future_field": "should be ignored",
        }
    ]
    tmp_file.write_text(json.dumps(data), encoding="utf-8")
    entries = load_history()
    assert len(entries) == 1
    assert entries[0].project_name == "test"
    assert not hasattr(entries[0], "future_field")


def test_clear_history():
    """clear_history removes all entries."""
    add_to_history(_make_entry())
    assert len(load_history()) == 1
    clear_history()
    assert load_history() == []


def test_make_history_entry_sets_timestamp():
    """make_history_entry creates entry with ISO timestamp."""
    entry = make_history_entry(
        project_name="test",
        project_path="/tmp",
        python_version="3.14",
        git_enabled=True,
        include_starter_files=False,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=False,
        project_type=None,
        folders=[],
        packages=[],
    )
    assert entry.built_at  # non-empty
    assert "T" in entry.built_at  # ISO format


def test_non_list_json_returns_empty(tmp_path, monkeypatch):
    """Returns empty list if JSON root is not a list."""
    tmp_file = tmp_path / "recent_projects.json"
    monkeypatch.setattr("uv_forger.core.history_manager.HISTORY_FILE", tmp_file)
    tmp_file.write_text('{"key": "value"}', encoding="utf-8")
    assert load_history() == []
