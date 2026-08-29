"""Data models for the project setup application.

This module defines the core data structures used throughout the application,
including project configuration, folder specifications, and build results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FolderSpec:
    """Specification for a folder in the project structure.

    Attributes:
        name: The folder name.
        create_init: Whether to create __init__.py in this folder (default: True).
        root_level: Whether this folder should be created at project root vs app/ (default: False).
        subfolders: List of nested folder specifications (default: None).
        files: List of file names to create in this folder (default: None).
    """

    name: str
    create_init: bool = True
    root_level: bool = False
    subfolders: list[str | FolderSpec] | None = None
    files: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert FolderSpec to a dictionary.

        Only includes fields with non-default values to minimize JSON output.
        Note: Not a lossless round-trip — default values (create_init=True,
        root_level=False) are omitted from the output.

        Returns:
            Dictionary representation of the folder specification.
        """
        result = {"name": self.name}
        # Only include non-default values to minimize JSON
        if not self.create_init:
            result["create_init"] = False
        if self.root_level:
            result["root_level"] = True
        if self.subfolders:
            result["subfolders"] = [
                sf.to_dict() if isinstance(sf, FolderSpec) else sf
                for sf in self.subfolders
            ]
        if self.files:
            result["files"] = self.files
        return result


@dataclass
class ProjectConfig:
    """Configuration for a project to be created.

    This dataclass holds all configuration needed to orchestrate project creation,
    including validation, directory setup, package installation, and git initialization.

    Attributes:
        project_name: Project name (must be non-empty and pass normalize_project_name validation).
        project_path: Base path where project will be created (must be an existing directory).
        python_version: Python version to use (e.g., "3.14").
        git_enabled: Whether to initialize a git repository (default: True).
        ui_project_enabled: Whether this is a UI project (default: False).
        framework: UI framework to install (e.g., "flet", "pyqt6"). Empty string if
            ui_project_enabled is False. If ui_project_enabled is True, framework
            should be non-empty and valid (default: "").
        other_project_enabled: Whether an other project type is selected (default: False).
        project_type: Project type (e.g., "django", "fastapi") for package/template
            installation. None if other_project_enabled is False. If other_project_enabled
            is True, project_type should be non-None and valid (default: None).
        include_starter_files: Whether to populate created files with starter content
            instead of creating empty files (default: True).
        folders: List of folder specifications defining the project structure. Can mix
            strings (folder names) and FolderSpec objects. Falls back to DEFAULT_FOLDERS
            if empty (default: []).
        packages: Explicit list of packages to install. When non-empty, overrides the
            packages derived from framework/project type maps (default: []).
        dev_packages: List of packages to install as dev dependencies (default: []).
        file_overrides: Mapping of canonical file paths to user-provided content (default: {}).
        user_boilerplate_dir: Optional path to user boilerplate overlay directory.
        github_root: Base directory for bare git hub repos, or None.
        git_remote_mode: Git remote strategy: "local", "github", or "none" (default: "local").
        github_username: GitHub username for repo creation (default: "").
        github_repo_private: Whether GitHub repos are created as private (default: True).
        author_name: Author name for pyproject.toml metadata (default: "").
        author_email: Author email for pyproject.toml metadata (default: "").
        description: Project description for pyproject.toml metadata (default: "").
        license_type: SPDX license identifier for pyproject.toml metadata (default: "").
    """

    project_name: str
    project_path: Path
    python_version: str
    git_enabled: bool = True
    ui_project_enabled: bool = False
    framework: str = ""
    other_project_enabled: bool = False
    project_type: str | None = None
    include_starter_files: bool = True
    folders: list[str | dict[str, Any] | FolderSpec] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    dev_packages: list[str] = field(default_factory=list)
    file_overrides: dict[str, str] = field(default_factory=dict)
    imported_structure: bool = False
    root_files: list[str] = field(default_factory=list)
    user_boilerplate_dir: Path | None = None
    github_root: Path | None = None
    git_remote_mode: str = "local"
    github_username: str = ""
    github_repo_private: bool = True
    author_name: str = ""
    author_email: str = ""
    description: str = ""
    license_type: str = ""

    @property
    def full_path(self) -> Path:
        """Get the full project path (base path + project name).

        Returns:
            Full path to the project directory.
        """
        return self.project_path / self.project_name

    @property
    def effective_framework(self) -> str | None:
        """Resolve the active UI framework, or None if UI is disabled.

        Returns:
            Framework name when ui_project_enabled is True, otherwise None.
        """
        return self.framework if self.ui_project_enabled else None

    @property
    def effective_project_type(self) -> str | None:
        """Resolve the active project type, or None if other project is disabled.

        Returns:
            Project type when other_project_enabled is True, otherwise None.
        """
        return self.project_type if self.other_project_enabled else None


@dataclass
class BuildResult:
    """Result of a project build operation.

    Attributes:
        success: Whether the build succeeded.
        message: Status or error message.
        error: Optional exception that occurred during build.
    """

    success: bool
    message: str
    error: Exception | None = None


@dataclass
class BuildSummaryConfig:
    """Configuration for build summary dialog display.

    Used to pass project configuration data to the build summary dialog for user
    review before project creation. The dialog displays this information and
    provides options to proceed with the build or cancel.

    Attributes:
        project_name: Name of the project.
        project_path: Base path where project will be created.
        python_version: Selected Python version (e.g., "3.14").
        git_enabled: Whether git repository initialization is enabled.
        ui_project_enabled: Whether a UI project was selected. If True, framework
            will be non-None; if False, framework will be None.
        framework: Selected UI framework name (e.g., "Flet"), or None if
            ui_project_enabled is False.
        other_project_enabled: Whether an other project type was selected. If True,
            project_type will be non-None; if False, project_type will be None.
        project_type: Selected project type (e.g., "django", "fastapi"), or None if
            other_project_enabled is False.
        starter_files: Whether starter files will be included in the project.
        folder_count: Number of folders to be created in the project.
        file_count: Number of files to be created in the project.
        packages: List of packages that will be installed (default: []).
        dev_packages: List of packages marked as dev dependencies (default: []).
        folders: Normalized folder structure for tree preview display.
        author_name: Author name for pyproject.toml metadata.
        author_email: Author email for pyproject.toml metadata.
        description: Project description for pyproject.toml metadata.
        license_type: SPDX license identifier for pyproject.toml metadata.
        file_override_count: Number of files with user-provided content overrides.
        post_build_command: Shell command to run after build.
        post_build_command_enabled: Whether the post-build command is enabled for this build.
        git_remote_mode: Git remote strategy: "local", "github", or "none".
        github_username: GitHub username for repo creation.
        github_repo_private: Whether GitHub repos are created as private.

    Note:
        ui_project_enabled and other_project_enabled are independent—both can be
        False, and in practice, at most one should typically be True (but the dialog
        handles all cases).
    """

    project_name: str
    project_path: str
    python_version: str
    git_enabled: bool
    ui_project_enabled: bool
    framework: str | None
    other_project_enabled: bool
    project_type: str | None
    starter_files: bool
    folder_count: int
    file_count: int
    packages: list[str] = field(default_factory=list)
    dev_packages: list[str] = field(default_factory=list)
    folders: list[str | dict] = field(default_factory=list)
    author_name: str = ""
    author_email: str = ""
    description: str = ""
    license_type: str = ""
    file_override_count: int = 0
    imported_structure: bool = False
    root_files: list[str] = field(default_factory=list)
    post_build_command: str = ""
    post_build_command_enabled: bool = False
    git_remote_mode: str = "local"
    github_username: str = ""
    github_repo_private: bool = True

    @classmethod
    def from_project_config(
        cls,
        config: ProjectConfig,
        folder_count: int,
        file_count: int,
        folders: list[str | dict],
    ) -> BuildSummaryConfig:
        """Create a BuildSummaryConfig from a ProjectConfig.

        Args:
            config: The project configuration to summarize.
            folder_count: Number of folders to be created.
            file_count: Number of files to be created.
            folders: Normalized folder structure for tree preview.

        Returns:
            BuildSummaryConfig instance.
        """
        return cls(
            project_name=config.project_name,
            project_path=str(config.project_path),
            python_version=config.python_version,
            git_enabled=config.git_enabled,
            ui_project_enabled=config.ui_project_enabled,
            framework=config.effective_framework,
            other_project_enabled=config.other_project_enabled,
            project_type=config.effective_project_type,
            starter_files=config.include_starter_files,
            folder_count=folder_count,
            file_count=file_count,
            packages=config.packages,
            dev_packages=config.dev_packages,
            folders=folders,
            imported_structure=config.imported_structure,
            root_files=list(config.root_files),
            author_name=config.author_name,
            author_email=config.author_email,
            description=config.description,
            license_type=config.license_type,
            git_remote_mode=config.git_remote_mode,
            github_username=config.github_username,
            github_repo_private=config.github_repo_private,
        )


def to_plain(value: Any) -> Any:
    """Recursively convert observable collections back to plain containers.

    ``AppState`` is decorated with ``@ft.observable``, which transparently wraps
    its ``list`` and ``dict`` fields in ``ObservableList`` / ``ObservableDict``
    so in-place mutation still notifies subscribers. Those wrappers subclass
    ``list`` and ``dict``, so they serialize fine through ``json.dumps`` — but
    ``dataclasses.asdict()`` rebuilds nested containers via ``type(obj)(...)``
    and their constructors require ``(owner, field)`` arguments, raising
    ``TypeError``. Call this on any state-derived structure before storing it in
    a dataclass that will later be passed to ``asdict()``.

    Args:
        value: Any value; nested lists and dicts are rebuilt as plain ones.

    Returns:
        The same data using only plain ``list`` and ``dict`` containers.
    """
    if isinstance(value, dict):
        return {key: to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    return value
