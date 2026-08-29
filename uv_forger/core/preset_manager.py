"""Project preset management for UV Forger.

Handles saving and loading named project presets to a JSON file in the
platform-appropriate data directory. Presets store a full project
configuration (framework, project type, packages, folders, etc.) that
can be applied to quickly set up a new project.
"""

import datetime
import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from uv_forger.core.models import to_plain
from uv_forger.core.settings_manager import SETTINGS_DIR

PRESETS_FILE = SETTINGS_DIR / "presets.json"


@dataclass
class ProjectPreset:
    """A named project configuration preset.

    Attributes:
        name: User-given label for this preset.
        python_version: Python version to use.
        git_enabled: Whether to initialize git.
        include_starter_files: Whether to populate files with starter content.
        ui_project_enabled: Whether a UI framework is selected.
        framework: Selected UI framework name, or None.
        other_project_enabled: Whether a project type is selected.
        project_type: Selected project type name, or None.
        folders: Folder structure.
        packages: Packages to install.
        dev_packages: Packages marked as dev dependencies.
        author_name: Default author name for pyproject.toml.
        author_email: Default author email for pyproject.toml.
        description: Project description for pyproject.toml.
        license_type: SPDX license identifier.
        saved_at: ISO-format timestamp of when the preset was saved.
        builtin: Whether this is a factory-provided preset (not user-created).
    """

    name: str
    python_version: str
    git_enabled: bool
    include_starter_files: bool
    ui_project_enabled: bool
    framework: str | None
    other_project_enabled: bool
    project_type: str | None
    folders: list[str | dict[str, Any]]
    packages: list[str]
    dev_packages: list[str] = field(default_factory=list)
    imported_structure: bool = False
    root_files: list[str] = field(default_factory=list)
    author_name: str = ""
    author_email: str = ""
    description: str = ""
    license_type: str = ""
    saved_at: str = ""
    builtin: bool = False

    def __post_init__(self) -> None:
        if not self.saved_at:
            self.saved_at = datetime.datetime.now(datetime.UTC).isoformat()


# ── Built-in starter presets ────────────────────────────────────────────────

BUILTIN_PRESETS: list[ProjectPreset] = [
    ProjectPreset(
        name="Flet Desktop App",
        python_version="3.13",
        git_enabled=True,
        include_starter_files=True,
        ui_project_enabled=True,
        framework="Flet",
        other_project_enabled=False,
        project_type=None,
        folders=[
            {
                "name": ".dev",
                "create_init": False,
                "root_level": True,
                "subfolders": ["experiments", "notes", "screens"],
            },
            {
                "name": "assets",
                "create_init": False,
                "subfolders": ["icons", "images", "themes", "docs"],
            },
            {
                "name": "core",
                "files": [
                    "async_executor.py",
                    "constants.py",
                    "logging_config.py",
                    "state.py",
                ],
            },
            {"name": "handlers", "files": ["handler_base", "ui_handler.py"]},
            {
                "name": "ui",
                "files": [
                    "components.py",
                    "dialogs.py",
                    "theme_manager.py",
                    "ui_config.py",
                ],
            },
            {
                "name": "tests",
                "root_level": True,
                "subfolders": ["core", "handlers", "ui"],
                "files": ["conftest.py", "test_app.py"],
            },
        ],
        packages=["flet", "pytest", "pytest-cov", "ruff"],
        dev_packages=["pytest", "pytest-cov", "ruff"],
        license_type="MIT",
        saved_at="",
        builtin=True,
    ),
    ProjectPreset(
        name="FastAPI Backend",
        python_version="3.13",
        git_enabled=True,
        include_starter_files=True,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=True,
        project_type="FastAPI",
        folders=[
            {
                "name": "api",
                "create_init": True,
                "subfolders": [
                    {
                        "name": "v1",
                        "create_init": True,
                        "subfolders": ["endpoints"],
                    }
                ],
                "files": ["dependencies.py"],
            },
            {
                "name": "core",
                "create_init": True,
                "files": ["config.py", "security.py"],
            },
            {"name": "models", "create_init": True, "files": ["base.py"]},
            {"name": "schemas", "create_init": True, "files": []},
            {"name": "services", "create_init": True, "files": []},
            {
                "name": "db",
                "create_init": True,
                "files": ["database.py", "session.py"],
            },
            {
                "name": "tests",
                "create_init": True,
                "root_level": True,
                "files": ["conftest.py", "test_app.py"],
                "subfolders": ["api", "unit"],
            },
        ],
        packages=[
            "fastapi",
            "uvicorn",
            "httpx",
            "pydantic",
            "pytest",
            "pytest-cov",
            "ruff",
        ],
        dev_packages=["pytest", "pytest-cov", "ruff"],
        license_type="MIT",
        saved_at="",
        builtin=True,
    ),
    ProjectPreset(
        name="Data Science Starter",
        python_version="3.13",
        git_enabled=True,
        include_starter_files=True,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=True,
        project_type="Data Analysis",
        folders=[
            {
                "name": "data",
                "create_init": False,
                "root_level": True,
                "subfolders": ["raw", "processed", "external"],
            },
            {
                "name": "notebooks",
                "create_init": False,
                "root_level": True,
                "subfolders": ["exploratory", "reports"],
            },
            {
                "name": "src",
                "create_init": True,
                "root_level": True,
                "subfolders": [
                    {"name": "data", "files": ["make_dataset.py"]},
                    {"name": "features", "files": ["build_features.py"]},
                    {"name": "visualization", "files": ["visualize.py"]},
                ],
            },
            {
                "name": "reports",
                "create_init": False,
                "root_level": True,
                "subfolders": ["figures"],
            },
            {
                "name": "models",
                "create_init": False,
                "root_level": True,
                "subfolders": [],
            },
        ],
        packages=["pandas", "numpy", "matplotlib", "jupyter"],
        dev_packages=[],
        license_type="MIT",
        saved_at="",
        builtin=True,
    ),
    ProjectPreset(
        name="CLI Tool (Typer)",
        python_version="3.13",
        git_enabled=True,
        include_starter_files=True,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=True,
        project_type="CLI (Typer)",
        folders=[
            {
                "name": "cli",
                "create_init": True,
                "files": ["main.py", "config.py", "utils.py"],
                "subfolders": [{"name": "commands", "files": []}],
            },
            {
                "name": "core",
                "create_init": True,
                "files": ["models.py", "validators.py"],
            },
            {
                "name": "utils",
                "create_init": True,
                "files": ["formatting.py", "helpers.py"],
            },
            {
                "name": "tests",
                "create_init": True,
                "root_level": True,
                "files": ["conftest.py", "test_app.py"],
                "subfolders": ["commands", "unit"],
            },
        ],
        packages=["typer[all]", "pytest", "pytest-cov", "ruff"],
        dev_packages=["pytest", "pytest-cov", "ruff"],
        license_type="MIT",
        saved_at="",
        builtin=True,
    ),
]


def _deserialize_list[T](data: Any, cls: type[T]) -> list[T]:
    """Deserialize a JSON list into dataclass instances, skipping malformed items."""
    if not isinstance(data, list):
        return []
    valid_keys = {f.name for f in fields(cls)}  # type: ignore[arg-type]
    result: list[T] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            result.append(cls(**{k: v for k, v in item.items() if k in valid_keys}))  # type: ignore[call-arg]
        except TypeError:
            continue
    return result


def load_presets() -> list[ProjectPreset]:
    """Load presets from disk.

    Returns:
        List of ProjectPreset, newest first. Empty list if file
        is missing or corrupted.
    """
    presets: list[ProjectPreset] = []

    if PRESETS_FILE.exists():
        try:
            data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None
        presets = _deserialize_list(data, ProjectPreset)

    # Append built-in presets that aren't shadowed by user presets of the same name
    user_names = {p.name for p in presets}
    for bp in BUILTIN_PRESETS:
        if bp.name not in user_names:
            presets.append(bp)

    return presets


def save_presets(presets: list[ProjectPreset]) -> None:
    """Write presets to disk as JSON.

    Creates the settings directory if it doesn't exist.

    Args:
        presets: List of ProjectPreset to persist.
    """
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(
        json.dumps([asdict(p) for p in presets], indent=2) + "\n",
        encoding="utf-8",
    )


def add_preset(preset: ProjectPreset) -> None:
    """Add or update a preset, deduplicating by name.

    The new preset is prepended. If a preset with the same name already
    exists, it is replaced.

    Args:
        preset: The ProjectPreset to add.
    """
    presets = load_presets()
    presets = [p for p in presets if p.name != preset.name]
    presets.insert(0, preset)
    save_presets([p for p in presets if not p.builtin])


def delete_preset(name: str) -> None:
    """Remove a preset by name.

    Built-in presets cannot be deleted.

    Args:
        name: The name of the preset to delete.
    """
    # Refuse to delete built-in presets
    builtin_names = {bp.name for bp in BUILTIN_PRESETS}
    if name in builtin_names:
        return

    presets = load_presets()
    presets = [p for p in presets if p.name != name]
    save_presets([p for p in presets if not p.builtin])


def make_preset(
    name: str,
    python_version: str,
    git_enabled: bool,
    include_starter_files: bool,
    ui_project_enabled: bool,
    framework: str | None,
    other_project_enabled: bool,
    project_type: str | None,
    folders: list,
    packages: list[str],
    dev_packages: list[str] | None = None,
    imported_structure: bool = False,
    root_files: list[str] | None = None,
    author_name: str = "",
    author_email: str = "",
    description: str = "",
    license_type: str = "",
) -> ProjectPreset:
    """Create a ProjectPreset with the current timestamp (set via __post_init__)."""
    return ProjectPreset(
        name=name,
        python_version=python_version,
        git_enabled=git_enabled,
        include_starter_files=include_starter_files,
        ui_project_enabled=ui_project_enabled,
        framework=framework,
        other_project_enabled=other_project_enabled,
        project_type=project_type,
        folders=to_plain(folders),
        packages=list(packages),
        dev_packages=list(dev_packages) if dev_packages else [],
        imported_structure=imported_structure,
        root_files=list(root_files) if root_files else [],
        author_name=author_name,
        author_email=author_email,
        description=description,
        license_type=license_type,
    )
