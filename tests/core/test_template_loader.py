"""Test suite for TemplateLoader class"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from uv_forger.core.template_loader import TemplateLoader


class TestTemplateLoaderInit:
    """Tests for TemplateLoader initialization"""

    def test_init_creates_valid_manager(self):
        """Test TemplateLoader initialization"""
        manager = TemplateLoader()

        # Check if settings is a dict (not a method object)
        assert isinstance(manager.settings, dict)

        # Check if settings has 'folders' key
        assert "folders" in manager.settings

        # Check if config_source is a Path
        assert isinstance(manager.config_source, Path)


class TestLoadTemplate:
    """Tests for template loading"""

    def test_returns_none_for_nonexistent_file(self):
        """Test returns None for non-existent file"""
        manager = TemplateLoader()
        result = manager._load_template(Path("/nonexistent/path.json"))
        assert result is None

    def test_loads_valid_json_template(self):
        """Test loads valid JSON file"""
        manager = TemplateLoader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"folders": ["src", "tests"]}, f)
            temp_path = Path(f.name)

        try:
            result = manager._load_template(temp_path)
            assert result is not None
            assert isinstance(result, dict)
            assert "folders" in result
        finally:
            temp_path.unlink()

    def test_returns_none_for_invalid_json(self):
        """Test returns None for invalid JSON file"""
        manager = TemplateLoader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)

        try:
            result = manager._load_template(temp_path)
            assert result is None
        finally:
            temp_path.unlink()


class TestLoadConfig:
    """Tests for config loading"""

    def test_load_config_without_template(self):
        """Test load without template (should use default)"""
        manager = TemplateLoader()
        config = manager.load_config()

        assert isinstance(config, dict)
        assert "folders" in config

    def test_load_config_with_nonexistent_template(self):
        """Test load with non-existent template (should fall back to default)"""
        manager = TemplateLoader()
        config = manager.load_config("nonexistent_framework")

        assert isinstance(config, dict)
        assert "folders" in config


class TestGetConfigDisplayName:
    """Tests for config display name generation"""

    def test_returns_valid_display_name(self):
        """Test returns valid display name"""
        manager = TemplateLoader()
        display_name = manager.get_config_display_name()

        assert isinstance(display_name, str)
        assert len(display_name) > 0
        assert display_name.endswith(" template")

    def test_display_name_includes_template_suffix(self):
        """Test display name always includes ' template' suffix"""
        manager = TemplateLoader()
        manager.load_config()
        display_name = manager.get_config_display_name()

        assert " template" in display_name
        assert display_name.endswith(" template")


class TestTemplateLoaderUserDir:
    """Tests for user_templates_dir overlay in TemplateLoader."""

    def test_init_stores_user_templates_dir(self):
        loader = TemplateLoader(user_templates_dir=Path("/my/templates"))
        assert loader.user_templates_dir == Path("/my/templates")

    def test_init_none_by_default(self):
        loader = TemplateLoader()
        assert loader.user_templates_dir is None

    def test_user_ui_framework_template_loaded(self):
        """User template for a UI framework takes precedence over bundled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir)
            fw_dir = user_dir / "ui_frameworks"
            fw_dir.mkdir(parents=True)
            template = {"folders": [{"name": "user_custom"}]}
            (fw_dir / "flet.json").write_text(json.dumps(template))

            loader = TemplateLoader(user_templates_dir=user_dir)
            config = loader.load_config("flet")

            assert config["folders"] == [{"name": "user_custom"}]
            assert "user" in str(loader.config_source).lower() or str(
                loader.config_source
            ).startswith(tmpdir)

    def test_user_project_type_template_loaded(self):
        """User template for a project type takes precedence over bundled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir)
            pt_dir = user_dir / "project_types"
            pt_dir.mkdir(parents=True)
            template = {"folders": [{"name": "user_django"}]}
            (pt_dir / "django.json").write_text(json.dumps(template))

            loader = TemplateLoader(user_templates_dir=user_dir)
            config = loader.load_config("project_types/django")

            assert config["folders"] == [{"name": "user_django"}]

    def test_falls_back_to_bundled_when_user_missing(self):
        """When user dir has no matching template, bundled is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir)  # empty, no templates

            loader = TemplateLoader(user_templates_dir=user_dir)
            config = loader.load_config("flet")

            # Should still load successfully from bundled
            assert isinstance(config, dict)
            assert "folders" in config

    def test_no_user_dir_preserves_existing_behavior(self):
        """None user_templates_dir means existing behavior."""
        loader = TemplateLoader(user_templates_dir=None)
        config = loader.load_config("flet")
        assert isinstance(config, dict)
        assert "folders" in config


class TestLoadConfigProjectTypePath:
    """Tests for load_config with project_type style paths (lines 101-102)."""

    def test_project_type_path_extracts_filename(self):
        """load_config with 'project_types/django' should load the django template."""
        manager = TemplateLoader()
        config = manager.load_config("project_types/django")

        assert isinstance(config, dict)
        assert "folders" in config
        # Loaded template name is stored
        assert manager.loaded_template == "project_types/django"

    def test_project_type_path_with_nested_slash(self):
        """Only the last segment after / is used as the filename."""
        manager = TemplateLoader()
        # Use a real project type that exists
        config = manager.load_config("project_types/fastapi")
        assert "folders" in config

    def test_framework_path_without_slash_normalizes(self):
        """Framework name without slash should load from ui_frameworks/ directory."""
        manager = TemplateLoader()
        config = manager.load_config("flet")
        assert "folders" in config
        assert manager.loaded_template == "flet"

    def test_nonexistent_project_type_falls_back(self):
        """Unknown project type falls through to default template."""
        manager = TemplateLoader()
        config = manager.load_config("project_types/nonexistent_xyz")
        assert "folders" in config

    def test_load_config_updates_config_source(self):
        """After successful load, config_source is updated (line 110-111)."""
        manager = TemplateLoader()
        manager.load_config("flet")
        # config_source should reflect the flet template path now
        assert "flet" in str(manager.config_source).lower()

    def test_fallback_to_default_folders_when_no_template(self):
        """When both specific and default templates fail, hardcoded defaults used (lines 121-122)."""
        manager = TemplateLoader()
        # Patch _load_template to always return None
        with patch.object(manager, "_load_template", return_value=None):
            config = manager.load_config("some_framework")

        assert "folders" in config
        # Should have fallen back to DEFAULT_FOLDERS
        from uv_forger.core.constants import DEFAULT_FOLDERS

        assert config["folders"] == DEFAULT_FOLDERS.copy()
