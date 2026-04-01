"""Filesystem operations for project structure creation.

This module handles creating directories, __init__.py files, and processing
nested folder structures from configuration specifications.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uv_forger.core.boilerplate_resolver import BoilerplateResolver


def create_folders(
    parent_dir: Path,
    folders: list[str | dict[str, Any]],
    parent_create_init: bool = True,
    resolver: BoilerplateResolver | None = None,
    skip_files: bool = False,
    file_overrides: dict[str, str] | None = None,
    _parent_canonical: str = "",
) -> None:
    """Recursively create directory structure from configuration.

    Processes folder specifications and creates the corresponding filesystem
    structure. Supports both simple string entries and complex nested objects
    with configuration options.

    Args:
        parent_dir: Parent directory where folders should be created.
        folders: List of folder specifications (strings or dict objects).
        parent_create_init: Whether parent's create_init setting was True (default: True).
        resolver: Optional BoilerplateResolver for populating files with starter content.
        skip_files: When True, skip creating template files (only dirs + __init__.py).

    Folder specification formats:
        - String: "core" -> creates core/ with __init__.py
        - Object: {
            "name": "assets",
            "create_init": false,
            "root_level": false,
            "subfolders": [...],
            "files": ["event_handlers.py", ...]
        }
    """
    for folder_spec in folders:
        if isinstance(folder_spec, str):
            # Simple string folder
            target = parent_dir / folder_spec
            target.mkdir(parents=True, exist_ok=True)
            if parent_create_init:
                (target / "__init__.py").touch()
        elif isinstance(folder_spec, dict):
            # Structured folder with possible subfolders and files
            folder_name = folder_spec.get("name", "")
            create_init = folder_spec.get("create_init", True)
            subfolders = folder_spec.get("subfolders", [])
            files = folder_spec.get("files", [])

            if not folder_name:
                continue

            target = parent_dir / folder_name
            target.mkdir(parents=True, exist_ok=True)
            if create_init:
                (target / "__init__.py").touch()

            # Create specified files in this folder
            canonical_prefix = (
                f"{_parent_canonical}{folder_name}/"
                if _parent_canonical
                else f"{folder_name}/"
            )
            if files and not skip_files:
                for file_name in files:
                    file_path = target / file_name
                    canonical_key = f"{canonical_prefix}{file_name}"
                    if file_overrides and canonical_key in file_overrides:
                        content = file_overrides[canonical_key]
                    else:
                        content = resolver.resolve(file_name) if resolver else None
                    if content is not None:
                        file_path.write_text(content, encoding="utf-8")
                    else:
                        file_path.touch()

            # Recursively create subfolders
            if subfolders:
                create_folders(
                    target,
                    subfolders,
                    create_init,
                    resolver,
                    skip_files,
                    file_overrides,
                    canonical_prefix,
                )


def setup_app_structure(
    project_path: Path,
    folders: list[str | dict[str, Any]],
    resolver: BoilerplateResolver | None = None,
    skip_files: bool = False,
    file_overrides: dict[str, str] | None = None,
) -> None:
    """Create app directory and configured folder structure.

    Creates the app/ directory with __init__.py, then processes the folder
    configuration to create root-level folders (at project root) and
    app-level folders (inside app/). Moves hello.py to app/main.py if present.

    Args:
        project_path: Path to the project directory.
        folders: List of folder specifications from configuration.
        resolver: Optional BoilerplateResolver for populating files with starter content.
        skip_files: When True, skip creating template files (only dirs + __init__.py).
    """
    app_dir = project_path / "app"
    app_dir.mkdir(exist_ok=True)
    (app_dir / "__init__.py").touch()

    # Separate folders into root-level and app-level
    root_folders = []
    app_folders = []

    for folder_spec in folders:
        if isinstance(folder_spec, dict) and folder_spec.get("root_level", False):
            root_folders.append(folder_spec)
        else:
            app_folders.append(folder_spec)

    # Create root-level folders at project root
    if root_folders:
        create_folders(
            project_path,
            root_folders,
            resolver=resolver,
            skip_files=skip_files,
            file_overrides=file_overrides,
        )

    # Create app-level folders inside app/
    if app_folders:
        create_folders(
            app_dir,
            app_folders,
            resolver=resolver,
            skip_files=skip_files,
            file_overrides=file_overrides,
        )

    # Move main.py to app/main.py if it exists (uv init creates main.py)
    main_py = project_path / "main.py"
    app_main = app_dir / "main.py"
    if main_py.exists():
        main_py.rename(app_main)

    # Replace UV's default main.py and README.md with boilerplate if available
    if resolver and not skip_files:
        content = resolver.resolve("main.py")
        if content is not None:
            app_main.write_text(content, encoding="utf-8")

        readme_content = resolver.resolve("README.md")
        if readme_content is not None:
            (project_path / "README.md").write_text(readme_content, encoding="utf-8")


# Files created by UV init / git that should not be duplicated
_UV_GENERATED_FILES = frozenset(
    {
        "pyproject.toml",
        ".gitignore",
        ".python-version",
        "README.md",
        "main.py",
        "uv.lock",
    }
)


def setup_imported_structure(
    project_path: Path,
    folders: list[str | dict[str, Any]],
    root_files: list[str] | None = None,
    resolver: BoilerplateResolver | None = None,
    skip_files: bool = False,
    file_overrides: dict[str, str] | None = None,
) -> None:
    """Create project structure from an imported tree at the project root.

    Unlike setup_app_structure(), this does NOT create an app/ directory.
    All folders are created directly at the project root, and root-level
    files from the imported tree are created (skipping UV-generated files).

    Args:
        project_path: Path to the project directory.
        folders: List of folder specifications from the imported tree.
        root_files: List of root-level file names from the imported tree.
        resolver: Optional BoilerplateResolver for populating files with starter content.
        skip_files: When True, skip creating template files (only dirs + __init__.py).
        file_overrides: Mapping of canonical file paths to user-provided content.
    """
    # Delete UV's main.py — imported structure defines its own layout
    uv_main = project_path / "main.py"
    if uv_main.exists():
        uv_main.unlink()

    # Create all folders at project root (no app/ nesting)
    if folders:
        create_folders(
            project_path,
            folders,
            parent_create_init=False,
            resolver=resolver,
            skip_files=skip_files,
            file_overrides=file_overrides,
        )

    # Create root-level files from imported tree
    if root_files and not skip_files:
        for file_name in root_files:
            file_path = project_path / file_name
            canonical_key = file_name
            has_override = file_overrides and canonical_key in file_overrides

            if file_name in _UV_GENERATED_FILES and not has_override:
                # UV created this file and no user override — leave as-is
                continue

            if has_override:
                # User override replaces UV-generated content or creates new file
                file_path.write_text(file_overrides[canonical_key], encoding="utf-8")
            elif not file_path.exists():
                file_path.touch()
