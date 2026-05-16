"""Tests for the settings manager module."""

import json
from pathlib import Path
from unittest.mock import patch

from uv_forger.core.settings_manager import (
    SETTINGS_DIR,
    SETTINGS_FILE,
    AppSettings,
    get_user_templates_dir,
    load_settings,
    save_settings,
)


class TestAppSettings:
    """Tests for AppSettings dataclass defaults."""

    def test_default_values(self):
        settings = AppSettings()
        assert settings.default_project_path == str(Path.home() / "Projects")
        assert settings.default_github_root == str(
            Path.home() / "Projects" / "git-repos"
        )
        assert settings.default_python_version == "3.14"
        assert settings.preferred_ide == "VS Code"
        assert settings.custom_ide_path == ""
        assert settings.git_enabled_default is True

    def test_post_build_command_default_empty(self):
        settings = AppSettings()
        assert settings.post_build_command == ""

    def test_post_build_command_enabled_default_false(self):
        settings = AppSettings()
        assert settings.post_build_command_enabled is False

    def test_custom_values(self):
        settings = AppSettings(
            default_project_path="/custom/path",
            preferred_ide="Cursor",
            git_enabled_default=False,
        )
        assert settings.default_project_path == "/custom/path"
        assert settings.preferred_ide == "Cursor"
        assert settings.git_enabled_default is False


class TestLoadSettings:
    """Tests for load_settings()."""

    def test_returns_defaults_when_no_file(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", tmp_path),
        ):
            settings = load_settings()
            assert settings.default_python_version == "3.14"
            assert settings.preferred_ide == "VS Code"
            # Should have written the file
            assert fake_file.exists()

    def test_writes_defaults_on_first_run(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", tmp_path),
        ):
            load_settings()
            data = json.loads(fake_file.read_text())
            assert data["preferred_ide"] == "VS Code"
            assert data["default_python_version"] == "3.14"

    def test_loads_from_existing_file(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        fake_file.write_text(
            json.dumps(
                {
                    "default_project_path": "/my/projects",
                    "default_github_root": "/my/repos",
                    "default_python_version": "3.13",
                    "preferred_ide": "PyCharm",
                    "custom_ide_path": "",
                    "git_enabled_default": False,
                }
            )
        )
        with patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file):
            settings = load_settings()
            assert settings.default_project_path == "/my/projects"
            assert settings.default_python_version == "3.13"
            assert settings.preferred_ide == "PyCharm"
            assert settings.git_enabled_default is False

    def test_ignores_unknown_keys(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        fake_file.write_text(
            json.dumps(
                {
                    "preferred_ide": "Zed",
                    "future_setting": "something",
                    "another_unknown": 42,
                }
            )
        )
        with patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file):
            settings = load_settings()
            assert settings.preferred_ide == "Zed"
            # Other fields get defaults
            assert settings.default_python_version == "3.14"

    def test_missing_keys_get_defaults(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        fake_file.write_text(json.dumps({"preferred_ide": "Cursor"}))
        with patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file):
            settings = load_settings()
            assert settings.preferred_ide == "Cursor"
            assert settings.default_python_version == "3.14"
            assert settings.git_enabled_default is True

    def test_corrupt_json_returns_defaults(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        fake_file.write_text("not valid json {{{")
        with patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file):
            settings = load_settings()
            assert settings.preferred_ide == "VS Code"

    def test_empty_file_returns_defaults(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        fake_file.write_text("")
        with patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file):
            settings = load_settings()
            assert settings.preferred_ide == "VS Code"


class TestSaveSettings:
    """Tests for save_settings()."""

    def test_saves_to_json(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", tmp_path),
        ):
            settings = AppSettings(preferred_ide="Cursor", git_enabled_default=False)
            save_settings(settings)
            data = json.loads(fake_file.read_text())
            assert data["preferred_ide"] == "Cursor"
            assert data["git_enabled_default"] is False

    def test_creates_directory(self, tmp_path):
        nested_dir = tmp_path / "sub" / "dir"
        fake_file = nested_dir / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", nested_dir),
        ):
            save_settings(AppSettings())
            assert fake_file.exists()

    def test_roundtrip(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", tmp_path),
        ):
            original = AppSettings(
                default_project_path="/test/path",
                preferred_ide="Zed",
                custom_ide_path="/usr/bin/zed",
                default_python_version="3.12",
                git_enabled_default=False,
            )
            save_settings(original)
            loaded = load_settings()
            assert loaded.default_project_path == original.default_project_path
            assert loaded.preferred_ide == original.preferred_ide
            assert loaded.custom_ide_path == original.custom_ide_path
            assert loaded.default_python_version == original.default_python_version
            assert loaded.git_enabled_default == original.git_enabled_default

    def test_post_build_command_roundtrip(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", tmp_path),
        ):
            original = AppSettings(post_build_command="uv run pytest")
            save_settings(original)
            loaded = load_settings()
            assert loaded.post_build_command == "uv run pytest"

    def test_missing_post_build_command_defaults_empty(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        fake_file.write_text(json.dumps({"preferred_ide": "VS Code"}))
        with patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file):
            settings = load_settings()
            assert settings.post_build_command == ""


class TestGetUserTemplatesDir:
    """Tests for get_user_templates_dir()."""

    def test_default_when_no_settings(self):
        result = get_user_templates_dir()
        assert result == SETTINGS_DIR / "templates"

    def test_default_when_custom_path_empty(self):
        settings = AppSettings(custom_templates_path="")
        result = get_user_templates_dir(settings)
        assert result == SETTINGS_DIR / "templates"

    def test_custom_path_used_when_set(self):
        settings = AppSettings(custom_templates_path="/my/custom/templates")
        result = get_user_templates_dir(settings)
        assert result == Path("/my/custom/templates")

    def test_default_when_settings_is_none(self):
        result = get_user_templates_dir(None)
        assert result == SETTINGS_DIR / "templates"

    def test_custom_templates_path_default_empty(self):
        settings = AppSettings()
        assert settings.custom_templates_path == ""

    def test_custom_templates_path_roundtrip(self, tmp_path):
        fake_file = tmp_path / "settings.json"
        with (
            patch("uv_forger.core.settings_manager.SETTINGS_FILE", fake_file),
            patch("uv_forger.core.settings_manager.SETTINGS_DIR", tmp_path),
        ):
            original = AppSettings(custom_templates_path="/my/templates")
            save_settings(original)
            loaded = load_settings()
            assert loaded.custom_templates_path == "/my/templates"


class TestSettingsConstants:
    """Tests for module-level constants."""

    def test_settings_dir_is_path(self):
        assert isinstance(SETTINGS_DIR, Path)

    def test_settings_file_is_in_settings_dir(self):
        assert SETTINGS_FILE.parent == SETTINGS_DIR
        assert SETTINGS_FILE.name == "settings.json"
