"""Project tree builder for build summary preview.

Builds Unicode box-drawing trees of project structures, both as plain
text lines (for testing) and as styled Flet controls (for UI display).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from uv_forger.ui.ui_config import UIConfig

if TYPE_CHECKING:
    from uv_forger.core.models import BuildSummaryConfig


def _build_root_entries(config: BuildSummaryConfig) -> tuple[list[dict | str], list]:
    """Build the root-level entries for the tree based on structure mode.

    Returns:
        Tuple of (root_entries, app_folders) where app_folders is only
        populated for non-imported structures.
    """
    if config.imported_structure:
        # Imported structure: UV files + imported root files + all folders at root
        uv_files = [".python-version", "README.md", "pyproject.toml"]
        if config.git_enabled:
            uv_files.insert(0, ".gitignore")

        # Merge imported root files, deduplicating against UV files
        uv_set = set(uv_files)
        extra_files = [f for f in config.root_files if f not in uv_set]

        root_entries: list[dict | str] = []
        root_entries.extend(uv_files)
        root_entries.extend(extra_files)
        root_entries.extend(config.folders)
        return root_entries, []

    # Standard app/ layout
    root_folders = []
    app_folders = []
    for folder in config.folders:
        if isinstance(folder, dict) and folder.get("root_level", False):
            root_folders.append(folder)
        else:
            app_folders.append(folder)

    root_files = [".python-version", "README.md", "pyproject.toml"]
    if config.git_enabled:
        root_files.insert(0, ".gitignore")

    root_entries = []
    root_entries.extend(root_files)
    root_entries.append("__app__")  # Sentinel for app/ directory
    root_entries.extend(root_folders)
    return root_entries, app_folders


def build_project_tree_lines(config: BuildSummaryConfig) -> list[str]:
    """Build a Unicode box-drawing tree of the full project structure.

    Includes root-level files created by UV init (pyproject.toml, README.md, etc.),
    the app/ directory with __init__.py and main.py, and all template folders/files.
    For imported structures, all folders appear at the project root instead of
    inside app/.

    Args:
        config: BuildSummaryConfig with project name, git_enabled, and folders.

    Returns:
        List of strings, one per tree line.
    """
    lines: list[str] = [f"{config.project_name}/"]

    root_entries, app_folders = _build_root_entries(config)

    def _add_entries(
        entries: list[dict | str], prefix: str, parent_create_init: bool = True
    ) -> None:
        """Recursively add tree entries with box-drawing prefixes."""
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            if isinstance(entry, str):
                if entry == "__app__":
                    _add_app_dir(prefix, connector, child_prefix)
                else:
                    lines.append(f"{prefix}{connector}{entry}")
            elif isinstance(entry, dict):
                _add_folder(entry, prefix, connector, child_prefix)

    def _add_subfolder(
        name: str,
        parent_create_init: bool,
        prefix: str,
        connector: str,
        child_prefix: str,
    ) -> None:
        """Add a string subfolder (inherits parent's create_init)."""
        lines.append(f"{prefix}{connector}{name}/")
        if parent_create_init:
            lines.append(f"{child_prefix}└── __init__.py")

    def _add_folder(
        folder: dict, prefix: str, connector: str, child_prefix: str
    ) -> None:
        """Add a template folder and its contents to the tree."""
        name = folder.get("name", "")
        lines.append(f"{prefix}{connector}{name}/")

        create_init = folder.get("create_init", True)

        # Collect all children: __init__.py, files, then subfolders
        file_children: list[str] = []
        if create_init:
            file_children.append("__init__.py")
        file_children.extend(folder.get("files", []) or [])

        subfolders = folder.get("subfolders", []) or []
        total = len(file_children) + len(subfolders)
        idx = 0

        for file in file_children:
            idx += 1
            is_last = idx == total
            conn = "└── " if is_last else "├── "
            lines.append(f"{child_prefix}{conn}{file}")

        for sf in subfolders:
            idx += 1
            is_last = idx == total
            conn = "└── " if is_last else "├── "
            sf_child_prefix = child_prefix + ("    " if is_last else "│   ")
            if isinstance(sf, str):
                _add_subfolder(sf, create_init, child_prefix, conn, sf_child_prefix)
            elif isinstance(sf, dict):
                _add_folder(sf, child_prefix, conn, sf_child_prefix)

    def _add_app_dir(prefix: str, connector: str, child_prefix: str) -> None:
        """Add the app/ directory with __init__.py, main.py, and template folders."""
        lines.append(f"{prefix}{connector}app/")

        app_children: list[dict | str] = ["__init__.py", "main.py"]
        app_children.extend(app_folders)
        _add_entries(app_children, child_prefix)

    _add_entries(root_entries, "")
    return lines


def build_project_tree_controls(config: BuildSummaryConfig) -> list[ft.Control]:
    """Build a list of Flet Row controls for the project tree with icons.

    Same structure as build_project_tree_lines() but returns styled Flet
    controls with folder/file icons matching the Subfolders container.

    Args:
        config: BuildSummaryConfig with project name, git_enabled, and folders.

    Returns:
        List of Flet Row controls for display in the tree preview.
    """
    controls: list[ft.Control] = []

    def _tree_row(prefix: str, connector: str, name: str, is_folder: bool) -> ft.Row:
        icon = ft.Icons.FOLDER if is_folder else ft.Icons.INSERT_DRIVE_FILE
        icon_color = (
            UIConfig.COLOR_FOLDER_ICON if is_folder else UIConfig.COLOR_FILE_ICON
        )
        text_color = None if is_folder else UIConfig.COLOR_FILE_TEXT
        display = f"{name}/" if is_folder else name

        return ft.Row(
            [
                ft.Text(
                    f"{prefix}{connector}",
                    size=11,
                    font_family="monospace",
                    no_wrap=True,
                    color=ft.Colors.GREY_600,
                ),
                ft.Icon(icon, size=12, color=icon_color),
                ft.Text(
                    display,
                    size=11,
                    font_family="monospace",
                    no_wrap=True,
                    color=text_color,
                ),
            ],
            spacing=2,
            tight=True,
        )

    # Root line
    controls.append(
        ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, size=12, color=UIConfig.COLOR_FOLDER_ICON),
                ft.Text(
                    f"{config.project_name}/",
                    size=11,
                    font_family="monospace",
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=2,
            tight=True,
        )
    )

    root_entries, app_folders = _build_root_entries(config)

    def _add_entries(entries: list[dict | str], prefix: str) -> None:
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            if isinstance(entry, str):
                if entry == "__app__":
                    _add_app_dir(prefix, connector, child_prefix)
                else:
                    controls.append(_tree_row(prefix, connector, entry, False))
            elif isinstance(entry, dict):
                _add_folder(entry, prefix, connector, child_prefix)

    def _add_subfolder(
        name: str,
        parent_create_init: bool,
        prefix: str,
        connector: str,
        child_prefix: str,
    ) -> None:
        controls.append(_tree_row(prefix, connector, name, True))
        if parent_create_init:
            controls.append(_tree_row(child_prefix, "└── ", "__init__.py", False))

    def _add_folder(
        folder: dict, prefix: str, connector: str, child_prefix: str
    ) -> None:
        name = folder.get("name", "")
        controls.append(_tree_row(prefix, connector, name, True))

        create_init = folder.get("create_init", True)
        file_children: list[str] = []
        if create_init:
            file_children.append("__init__.py")
        file_children.extend(folder.get("files", []) or [])

        subfolders = folder.get("subfolders", []) or []
        total = len(file_children) + len(subfolders)
        idx = 0

        for file in file_children:
            idx += 1
            is_last = idx == total
            conn = "└── " if is_last else "├── "
            controls.append(_tree_row(child_prefix, conn, file, False))

        for sf in subfolders:
            idx += 1
            is_last = idx == total
            conn = "└── " if is_last else "├── "
            sf_child_prefix = child_prefix + ("    " if is_last else "│   ")
            if isinstance(sf, str):
                _add_subfolder(sf, create_init, child_prefix, conn, sf_child_prefix)
            elif isinstance(sf, dict):
                _add_folder(sf, child_prefix, conn, sf_child_prefix)

    def _add_app_dir(prefix: str, connector: str, child_prefix: str) -> None:
        controls.append(_tree_row(prefix, connector, "app", True))
        app_children: list[dict | str] = ["__init__.py", "main.py"]
        app_children.extend(app_folders)
        _add_entries(app_children, child_prefix)

    _add_entries(root_entries, "")
    return controls
