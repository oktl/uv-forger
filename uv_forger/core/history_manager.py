"""Recent project history management for UV Forger.

Handles loading and saving project build history to a JSON file in the
platform-appropriate data directory. Each successful build is recorded
so users can restore a previous project's full configuration.
"""

import datetime
import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from uv_forger.core.settings_manager import SETTINGS_DIR

MAX_HISTORY_ENTRIES = 5
HISTORY_FILE = SETTINGS_DIR / "recent_projects.json"


@dataclass
class ProjectHistoryEntry:
    """A single project build history record.

    Attributes:
        project_name: Name of the project.
        project_path: Base directory where the project was created.
        python_version: Python version used.
        git_enabled: Whether git was initialized.
        include_starter_files: Whether starter files were included.
        ui_project_enabled: Whether a UI framework was selected.
        framework: Selected UI framework name, or None.
        other_project_enabled: Whether an other project type was selected.
        project_type: Selected project type name, or None.
        folders: Folder structure at build time.
        packages: Packages installed at build time.
        dev_packages: Packages marked as dev dependencies at build time.
        built_at: ISO-format timestamp of the build.
    """

    project_name: str
    project_path: str
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
    built_at: str = ""

    def __post_init__(self) -> None:
        if not self.built_at:
            self.built_at = datetime.datetime.now(datetime.UTC).isoformat()


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


def load_history() -> list[ProjectHistoryEntry]:
    """Load project history from disk.

    Returns:
        List of ProjectHistoryEntry, newest first. Empty list if file
        is missing or corrupted.
    """
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    return _deserialize_list(data, ProjectHistoryEntry)


def save_history(entries: list[ProjectHistoryEntry]) -> None:
    """Write history entries to disk as JSON.

    Creates the settings directory if it doesn't exist.

    Args:
        entries: List of ProjectHistoryEntry to persist.
    """
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps([asdict(e) for e in entries], indent=2) + "\n",
        encoding="utf-8",
    )


def add_to_history(entry: ProjectHistoryEntry) -> None:
    """Add an entry to history, deduplicating by name+path.

    The new entry is prepended. If an entry with the same project_name
    and project_path already exists, it is replaced. The list is capped
    at MAX_HISTORY_ENTRIES.

    Args:
        entry: The ProjectHistoryEntry to add.
    """
    entries = load_history()

    # Remove duplicate (same name + path)
    entries = [
        e
        for e in entries
        if not (
            e.project_name == entry.project_name
            and e.project_path == entry.project_path
        )
    ]

    # Prepend and cap
    entries.insert(0, entry)
    entries = entries[:MAX_HISTORY_ENTRIES]

    save_history(entries)


def clear_history() -> None:
    """Remove all history entries from disk."""
    save_history([])


def make_history_entry(
    project_name: str,
    project_path: str,
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
) -> ProjectHistoryEntry:
    """Create a ProjectHistoryEntry with the current timestamp (set via __post_init__)."""
    return ProjectHistoryEntry(
        project_name=project_name,
        project_path=project_path,
        python_version=python_version,
        git_enabled=git_enabled,
        include_starter_files=include_starter_files,
        ui_project_enabled=ui_project_enabled,
        framework=framework,
        other_project_enabled=other_project_enabled,
        project_type=project_type,
        folders=list(folders),
        packages=list(packages),
        dev_packages=list(dev_packages) if dev_packages else [],
        imported_structure=imported_structure,
        root_files=list(root_files) if root_files else [],
    )
