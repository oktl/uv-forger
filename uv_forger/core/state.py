"""Application state management for UV Forger.

This module defines the AppState dataclass that holds all mutable application
state, including project configuration, UI state, and validation status.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, fields
from typing import Any, Literal

from uv_forger.core.settings_manager import AppSettings


@dataclass
class AppState:
    """Container for application state data.

    Attributes:
        settings: Persisted user settings (IDE preference, default paths, etc.).
        project_path: Base directory where project will be created.
        project_name: Name of the project to create.
        python_version: Python version for the project.
        git_enabled: Whether to create a git repository.
        include_starter_files: Whether to populate files with starter content.
        ui_project_enabled: Whether this is a UI framework project.
        framework: Selected UI framework (if ui_project_enabled is True).
        other_project_enabled: Whether an other project type is selected.
        project_type: Selected project type (if other_project_enabled is True).
        author_name: Author name for pyproject.toml metadata.
        author_email: Author email for pyproject.toml metadata.
        description: Project description for pyproject.toml metadata.
        license_type: SPDX license identifier for pyproject.toml metadata.
        folders: Current folder structure from template.
        selected_item_path: Path to selected item for folder/file removal.
        selected_item_type: Whether selected item is a "folder" or "file".
        packages: List of packages to install (pre-populated from framework/project type, user-editable).
        auto_packages: Last set of packages derived from maps; used to distinguish user additions from auto ones.
        dev_packages: Set of package names marked as dev dependencies.
        selected_package_idx: Index of selected package for removal, or None.
        file_overrides: Mapping of canonical file paths to imported content.
        is_dark_mode: Whether dark theme is active.
        active_dialog: Callable to dismiss the currently open dialog, or None.
        path_valid: Whether the current path passes validation.
        name_valid: Whether the current project name passes validation.
    """

    # User settings (persisted to disk, not reset)
    settings: AppSettings = field(default_factory=AppSettings)

    # Path and project settings — defaults pulled from settings in __post_init__
    project_path: str = ""
    project_name: str = ""

    # Options
    python_version: str = ""
    git_enabled: bool = True
    include_starter_files: bool = True
    ui_project_enabled: bool = False
    framework: str | None = None
    other_project_enabled: bool = False
    project_type: str | None = None

    # Project metadata (for pyproject.toml)
    author_name: str = ""
    author_email: str = ""
    description: str = ""
    license_type: str = ""

    # Folder management
    folders: list[str | dict[str, Any]] = field(default_factory=list)
    folders_modified: bool = False  # Set when user adds/removes/edits folders or files
    imported_structure: bool = False  # True when folders came from Import Tree
    root_files: list[str] = field(default_factory=list)  # Root-level files from import

    # Selection tracking for folder/file removal
    selected_item_path: list[int | str] | None = None
    selected_item_type: Literal["folder", "file"] | None = None

    # Package management
    packages: list[str] = field(default_factory=list)
    auto_packages: list[str] = field(
        default_factory=list
    )  # map-derived; used to detect manual additions
    dev_packages: set[str] = field(
        default_factory=set
    )  # package names marked as dev dependencies
    selected_package_idx: int | None = None

    # File content overrides (canonical_path -> content)
    file_overrides: dict[str, str] = field(default_factory=dict)

    # UI state
    is_dark_mode: bool = True
    active_dialog: Callable[[], None] | None = None  # Currently open dismissible dialog

    # Validation state
    path_valid: bool = True  # Default path is valid
    name_valid: bool = False  # Empty name is invalid

    def __post_init__(self) -> None:
        """Apply settings-based defaults when fields are left at sentinel values."""
        if not self.project_path:
            self.project_path = self.settings.default_project_path
        if not self.python_version:
            self.python_version = self.settings.default_python_version
        self.git_enabled = self.settings.git_enabled_default
        self.include_starter_files = self.settings.starter_files_default
        if not self.license_type:
            self.license_type = self.settings.default_license
        if not self.author_name:
            self.author_name = self.settings.default_author_name
        if not self.author_email:
            self.author_email = self.settings.default_author_email

    def reset(self) -> None:
        """Reset state to initial values.

        Preserves is_dark_mode and settings since those persist across resets.
        """
        preserved_dark_mode = self.is_dark_mode
        preserved_settings = self.settings
        fresh = AppState(settings=preserved_settings)
        for attr in fields(self):
            setattr(self, attr.name, getattr(fresh, attr.name))
        self.is_dark_mode = preserved_dark_mode
