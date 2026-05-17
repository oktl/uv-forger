"""Template loader for folder structure configurations.

This module handles loading folder structure configurations from templates.
Templates are organized in subdirectories:
- app/config/templates/ui_frameworks/ - UI framework templates (Flet, PyQt6, etc.)
- app/config/templates/project_types/ - Project type templates (Django, FastAPI, etc.)
- app/config/templates/default.json - Generic default template (fallback)
"""

import json
from pathlib import Path
from typing import Any

from uv_forger.core.boilerplate_resolver import normalize_framework_name
from uv_forger.core.constants import (
    DEFAULT_FOLDERS,
    PROJECT_TYPE_TEMPLATES_DIR,
    TEMPLATES_DIR,
    UI_TEMPLATES_DIR,
)


class TemplateLoader:
    """Manages loading folder configuration from templates.

    Loads folder structure templates from organized subdirectories:
    - UI frameworks: app/config/templates/ui_frameworks/ (e.g., flet.json, pyqt6.json)
    - Project types: app/config/templates/project_types/ (e.g., django.json, fastapi.json)

    Attributes:
        user_templates_dir: Optional path to user templates overlay directory.
        config_source: Path to the active template file being used.
        settings: Current configuration dictionary with 'folders' key.
        loaded_template: Template identifier that was loaded (e.g., "flet", "project_types/django").
    """

    def __init__(self, user_templates_dir: Path | None = None):
        """Initialize TemplateLoader and load default settings.

        Args:
            user_templates_dir: Optional path to user templates overlay directory.
                Templates found here take precedence over bundled templates.
        """
        self.user_templates_dir = user_templates_dir
        self.config_source: Path = TEMPLATES_DIR / "default.json"
        self.loaded_template: str | None = None
        self.settings: dict[str, Any] = self.load_config()

    def _load_template(self, template_path: Path) -> dict[str, Any] | None:
        """Load and parse a template file.

        Args:
            template_path: Path to the JSON template file.

        Returns:
            Dictionary containing configuration with 'folders' key, or None if
            the file doesn't exist or cannot be parsed.
        """
        if not template_path.exists():
            return None
        _template_errors = (json.JSONDecodeError, OSError)
        try:
            with open(template_path) as f:
                data = json.load(f)
                return {"folders": data.get("folders", DEFAULT_FOLDERS.copy())}
        except _template_errors:
            return None

    def _try_user_template(
        self, subdir: str, filename: str, template_id: str
    ) -> dict[str, Any] | None:
        """Try loading a template from the user overlay directory."""
        if not self.user_templates_dir:
            return None
        path = self.user_templates_dir / subdir / f"{filename}.json"
        settings = self._load_template(path)
        if settings:
            self.config_source = path
            self.loaded_template = template_id
            self.settings = settings
        return settings

    def load_config(self, template: str | None = None) -> dict[str, Any]:
        """Load folder configuration from template files.

        Precedence:
        1. Template-specific configuration (if template specified)
            - Handles both UI frameworks (e.g., "flet") and project types (e.g., "project_types/django")
        2. Default template (templates/default.json)
        3. Hard-coded DEFAULT_FOLDERS constant

        Args:
            template: Optional template identifier to load.
                    Can be a UI framework name like "flet"
                    or a project type path like "project_types/django".

        Returns:
            Dictionary containing 'folders' key with folder structure configuration.
        """
        defaults = {"folders": DEFAULT_FOLDERS.copy()}

        # Try template-specific configuration
        if template:
            # Check if it's a project type path (e.g., "project_types/django")
            if "/" in template:
                filename = template.split("/")[-1]
                user_settings = self._try_user_template(
                    "project_types", filename, template
                )
                if user_settings:
                    return user_settings
                template_path = PROJECT_TYPE_TEMPLATES_DIR / f"{filename}.json"
            else:
                # UI framework - look in ui_frameworks directory
                normalized = normalize_framework_name(template)
                user_settings = self._try_user_template(
                    "ui_frameworks", normalized, template
                )
                if user_settings:
                    return user_settings
                template_path = UI_TEMPLATES_DIR / f"{normalized}.json"

            settings = self._load_template(template_path)
            if settings:
                self.config_source = template_path
                self.loaded_template = template
                self.settings = settings
                return settings

        # Fall back to default template
        default_template = TEMPLATES_DIR / "default.json"
        settings = self._load_template(default_template)
        if settings:
            self.config_source = default_template
            self.loaded_template = template
            self.settings = settings
            return settings

        # Final fallback to hard-coded defaults
        self.config_source = default_template
        self.loaded_template = template
        self.settings = defaults
        return defaults

    def get_config_display_name(self) -> str:
        """Get a user-friendly name for the active config source.

        Returns:
            String like "default template", "flet template", "pyqt6 template", etc.
        """
        # Get template filename without extension
        template_name = self.config_source.stem
        return f"{template_name} template"
