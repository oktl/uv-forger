"""Tests for app.core.preset_manager."""

import json

import pytest

from uv_forger.core.preset_manager import (
    BUILTIN_PRESETS,
    ProjectPreset,
    add_preset,
    delete_preset,
    load_presets,
    make_preset,
    save_presets,
)

_N_BUILTIN = len(BUILTIN_PRESETS)


def _make_preset(name: str = "My Stack", **kwargs):
    """Create a test preset with sensible defaults."""
    defaults = {
        "name": name,
        "python_version": "3.14",
        "git_enabled": True,
        "include_starter_files": True,
        "ui_project_enabled": False,
        "framework": None,
        "other_project_enabled": False,
        "project_type": None,
        "folders": ["core", "utils"],
        "packages": ["httpx"],
        "saved_at": "2026-02-19T10:00:00+00:00",
    }
    defaults.update(kwargs)
    return ProjectPreset(**defaults)


@pytest.fixture(autouse=True)
def _use_tmp_presets(tmp_path, monkeypatch):
    """Redirect PRESETS_FILE to a temp directory for every test."""
    tmp_file = tmp_path / "presets.json"
    monkeypatch.setattr("uv_forger.core.preset_manager.PRESETS_FILE", tmp_file)
    monkeypatch.setattr("uv_forger.core.preset_manager.SETTINGS_DIR", tmp_path)


def test_load_empty():
    """Returns only built-in presets when no file exists."""
    presets = load_presets()
    assert len(presets) == _N_BUILTIN
    assert all(p.builtin for p in presets)


def test_save_and_load_roundtrip():
    """Presets survive a save/load cycle."""
    preset = _make_preset()
    save_presets([preset])
    loaded = load_presets()
    assert len(loaded) == 1 + _N_BUILTIN
    assert loaded[0].name == "My Stack"
    assert loaded[0].packages == ["httpx"]


def test_add_preset_prepends():
    """New preset is added at the front."""
    add_preset(_make_preset(name="First"))
    add_preset(_make_preset(name="Second"))
    presets = load_presets()
    assert len(presets) == 2 + _N_BUILTIN
    assert presets[0].name == "Second"
    assert presets[1].name == "First"


def test_deduplication_by_name():
    """Same name replaces old preset at top."""
    add_preset(_make_preset(name="dup", packages=["old-pkg"]))
    add_preset(_make_preset(name="other"))
    add_preset(_make_preset(name="dup", packages=["new-pkg"]))

    presets = load_presets()
    assert len(presets) == 2 + _N_BUILTIN
    assert presets[0].name == "dup"
    assert presets[0].packages == ["new-pkg"]


def test_delete_preset():
    """Delete removes preset by name."""
    add_preset(_make_preset(name="keep"))
    add_preset(_make_preset(name="remove"))
    delete_preset("remove")

    presets = load_presets()
    assert len(presets) == 1 + _N_BUILTIN
    assert presets[0].name == "keep"


def test_delete_nonexistent():
    """Delete of nonexistent name is a no-op."""
    add_preset(_make_preset(name="only"))
    delete_preset("ghost")
    assert len(load_presets()) == 1 + _N_BUILTIN


def test_no_cap_on_count():
    """Unlike history, presets have no entry limit."""
    for i in range(25):
        add_preset(_make_preset(name=f"preset-{i}"))
    assert len(load_presets()) == 25 + _N_BUILTIN


def test_corrupt_file_returns_only_builtins(tmp_path, monkeypatch):
    """Corrupt JSON returns only built-in presets."""
    tmp_file = tmp_path / "presets.json"
    monkeypatch.setattr("uv_forger.core.preset_manager.PRESETS_FILE", tmp_file)
    tmp_file.write_text("not json at all", encoding="utf-8")
    presets = load_presets()
    assert len(presets) == _N_BUILTIN
    assert all(p.builtin for p in presets)


def test_non_list_json_returns_only_builtins(tmp_path, monkeypatch):
    """JSON that is not a list returns only built-in presets."""
    tmp_file = tmp_path / "presets.json"
    monkeypatch.setattr("uv_forger.core.preset_manager.PRESETS_FILE", tmp_file)
    tmp_file.write_text('{"name": "oops"}', encoding="utf-8")
    presets = load_presets()
    assert len(presets) == _N_BUILTIN
    assert all(p.builtin for p in presets)


def test_unknown_keys_ignored(tmp_path, monkeypatch):
    """Future keys in JSON are silently dropped."""
    tmp_file = tmp_path / "presets.json"
    monkeypatch.setattr("uv_forger.core.preset_manager.PRESETS_FILE", tmp_file)
    data = [
        {
            "name": "test",
            "python_version": "3.14",
            "git_enabled": True,
            "include_starter_files": False,
            "ui_project_enabled": False,
            "framework": None,
            "other_project_enabled": False,
            "project_type": None,
            "folders": [],
            "packages": [],
            "future_field": "ignored",
        }
    ]
    tmp_file.write_text(json.dumps(data), encoding="utf-8")
    presets = load_presets()
    assert len(presets) == 1 + _N_BUILTIN
    assert presets[0].name == "test"
    assert not hasattr(presets[0], "future_field")


def test_invalid_entry_skipped(tmp_path, monkeypatch):
    """Entries missing required fields are skipped, built-ins still appear."""
    tmp_file = tmp_path / "presets.json"
    monkeypatch.setattr("uv_forger.core.preset_manager.PRESETS_FILE", tmp_file)
    data = [{"name": "incomplete"}, "not a dict"]
    tmp_file.write_text(json.dumps(data), encoding="utf-8")
    presets = load_presets()
    assert len(presets) == _N_BUILTIN
    assert all(p.builtin for p in presets)


def test_make_preset_sets_timestamp():
    """make_preset fills saved_at with an ISO timestamp."""
    preset = make_preset(
        name="ts-test",
        python_version="3.14",
        git_enabled=True,
        include_starter_files=True,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=False,
        project_type=None,
        folders=["core"],
        packages=["flask"],
    )
    assert preset.saved_at
    assert "T" in preset.saved_at


def test_dev_packages_preserved():
    """Dev packages roundtrip through save/load."""
    preset = _make_preset(dev_packages=["pytest", "ruff"])
    save_presets([preset])
    loaded = load_presets()
    assert loaded[0].dev_packages == ["pytest", "ruff"]


def test_metadata_fields_preserved():
    """Author, email, description, license roundtrip."""
    preset = _make_preset(
        author_name="Alice",
        author_email="alice@example.com",
        description="My project",
        license_type="MIT",
    )
    save_presets([preset])
    loaded = load_presets()
    assert loaded[0].author_name == "Alice"
    assert loaded[0].author_email == "alice@example.com"
    assert loaded[0].description == "My project"
    assert loaded[0].license_type == "MIT"


def test_framework_and_project_type():
    """Framework and project type are stored correctly."""
    preset = _make_preset(
        ui_project_enabled=True,
        framework="Flet",
        other_project_enabled=True,
        project_type="FastAPI",
    )
    save_presets([preset])
    loaded = load_presets()
    assert loaded[0].framework == "Flet"
    assert loaded[0].project_type == "FastAPI"
    assert loaded[0].ui_project_enabled is True
    assert loaded[0].other_project_enabled is True


# ── Built-in presets ──────────────────────────────────────────────────────


class TestBuiltinPresets:
    """Tests for built-in starter presets."""

    def test_builtin_presets_returned_when_no_user_presets(self):
        """load_presets() returns built-in presets when no file exists."""
        presets = load_presets()
        assert len(presets) == len(BUILTIN_PRESETS)
        for p in presets:
            assert p.builtin is True

    def test_builtin_presets_appended_after_user_presets(self):
        """User presets come first, built-ins after."""
        user = _make_preset(name="My Custom")
        save_presets([user])
        presets = load_presets()
        assert presets[0].name == "My Custom"
        assert presets[0].builtin is False
        # Built-ins follow
        builtin_names = {bp.name for bp in BUILTIN_PRESETS}
        for p in presets[1:]:
            assert p.name in builtin_names

    def test_delete_refuses_builtin(self):
        """delete_preset() is a no-op for built-in preset names."""
        before = load_presets()
        delete_preset("Flet Desktop App")
        after = load_presets()
        assert len(after) == len(before)
        assert any(p.name == "Flet Desktop App" for p in after)

    def test_builtin_presets_have_correct_names(self):
        """All 4 expected built-in presets exist."""
        names = {p.name for p in BUILTIN_PRESETS}
        assert names == {
            "Flet Desktop App",
            "FastAPI Backend",
            "Data Science Starter",
            "CLI Tool (Typer)",
        }

    def test_builtin_presets_all_have_builtin_true(self):
        """Every built-in preset has builtin=True."""
        for p in BUILTIN_PRESETS:
            assert p.builtin is True

    def test_builtin_presets_have_valid_fields(self):
        """Built-in presets have required non-empty fields."""
        for p in BUILTIN_PRESETS:
            assert p.python_version == "3.13"
            assert p.git_enabled is True
            assert p.include_starter_files is True
            assert p.license_type == "MIT"
            assert len(p.packages) > 0
            assert len(p.folders) > 0

    def test_builtin_not_persisted_to_disk(self, tmp_path):
        """Built-in presets are not written to disk."""
        import uv_forger.core.preset_manager as pm

        user = _make_preset(name="Mine")
        add_preset(user)
        raw = json.loads(pm.PRESETS_FILE.read_text(encoding="utf-8"))
        raw_names = {item["name"] for item in raw}
        # Only the user preset is on disk
        assert "Mine" in raw_names
        builtin_names = {bp.name for bp in BUILTIN_PRESETS}
        assert raw_names.isdisjoint(builtin_names)

    def test_user_preset_with_same_name_shadows_builtin(self):
        """A user preset with the same name as a built-in replaces it."""
        user = _make_preset(name="Flet Desktop App", packages=["custom-pkg"])
        save_presets([user])
        presets = load_presets()
        flet_presets = [p for p in presets if p.name == "Flet Desktop App"]
        assert len(flet_presets) == 1
        assert flet_presets[0].packages == ["custom-pkg"]
