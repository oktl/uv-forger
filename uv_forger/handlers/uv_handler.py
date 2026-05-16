"""UV package manager operations.

This module handles all interactions with the uv package manager,
including project initialization, virtual environment creation, and
package installation.
"""

import shutil
import subprocess
from pathlib import Path


def get_uv_path() -> str:
    """Get the full path to the uv executable.

    Returns:
        Full path to uv executable.

    Raises:
        FileNotFoundError: If uv cannot be found.
    """
    # Try to find uv in PATH
    uv_path = shutil.which("uv")

    # If not in PATH, check common installation locations
    if uv_path is None:
        import platform

        is_windows = platform.system() == "Windows"
        uv_name = "uv.exe" if is_windows else "uv"

        common_paths = [
            Path.home() / ".local" / "bin" / uv_name,
            Path.home() / ".cargo" / "bin" / uv_name,
        ]

        # Add Unix-specific paths
        if not is_windows:
            common_paths.append(Path("/usr/local/bin/uv"))

        for path in common_paths:
            if path.exists():
                uv_path = str(path)
                break

    if uv_path is None:
        raise FileNotFoundError(
            "Could not find 'uv' executable. Please ensure uv is installed."
        )

    return uv_path


def run_uv_init(project_path: Path, python_version: str) -> None:
    """Initialize a new UV project with specified Python version.

    Runs 'uv init --python <version> .' in the project directory.

    Args:
        project_path: Path to the project directory.
        python_version: Python version string (e.g., "3.14").

    Raises:
        subprocess.CalledProcessError: If uv init command fails.
    """
    uv_path = get_uv_path()
    subprocess.run(
        [uv_path, "init", "--python", python_version, "."],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True,
    )


def setup_virtual_env(project_path: Path, python_version: str) -> None:
    """Create virtual environment and sync dependencies.

    Runs 'uv venv --python <version>' followed by 'uv sync' to create
    and populate the virtual environment.

    Args:
        project_path: Path to the project directory.
        python_version: Python version string (e.g., "3.14").

    Raises:
        subprocess.CalledProcessError: If uv commands fail.
    """
    uv_path = get_uv_path()
    subprocess.run(
        [uv_path, "venv", "--python", python_version],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [uv_path, "sync"],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True,
    )


def install_packages(
    project_path: Path, package_names: list[str], *, dev: bool = False
) -> None:
    """Install multiple packages in a single uv add invocation.

    Resolves all dependencies together in one subprocess call.

    Args:
        project_path: Path to the project directory.
        package_names: List of package names to install. No-op if empty.
        dev: If True, install as dev dependencies via ``uv add --dev``.

    Raises:
        subprocess.CalledProcessError: If uv add command fails.
    """
    if not package_names:
        return
    uv_path = get_uv_path()
    cmd = [uv_path, "add"]
    if dev:
        cmd.append("--dev")
    cmd.extend(package_names)
    subprocess.run(
        cmd,
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True,
    )


def _resolve_entry_point(
    framework: str | None = None,
    project_type: str | None = None,
) -> str | None:
    """Resolve the entry point for a project based on framework and project type.

    Priority: framework > project_type > default.
    Returns None when the project type/framework has its own runner
    (e.g., Django, FastAPI, Streamlit).

    Args:
        framework: UI framework name, or None.
        project_type: Project type name, or None.

    Returns:
        Entry point string like "app.main:main", or None if no scripts section needed.
    """
    from uv_forger.core.constants import (
        DEFAULT_ENTRY_POINT,
        FRAMEWORK_ENTRY_POINT_MAP,
        PROJECT_TYPE_ENTRY_POINT_MAP,
    )

    if framework is not None:
        return FRAMEWORK_ENTRY_POINT_MAP.get(framework, DEFAULT_ENTRY_POINT)
    if project_type is not None:
        return PROJECT_TYPE_ENTRY_POINT_MAP.get(project_type, DEFAULT_ENTRY_POINT)
    return DEFAULT_ENTRY_POINT


def configure_pyproject(
    project_path: Path,
    project_name: str,
    framework: str | None = None,
    project_type: str | None = None,
    author_name: str = "",
    author_email: str = "",
    description: str = "",
    license_type: str = "",
    imported_structure: bool = False,
) -> None:
    """Update pyproject.toml with package, entry point, and metadata configuration.

    Appends hatch build configuration and, when appropriate, a project
    scripts entry point to the existing pyproject.toml file. Also modifies
    the [project] section to set authors, description, and license when provided.

    When imported_structure is True, skips hatch build config and entry point
    since the imported project defines its own layout.

    Args:
        project_path: Path to the project directory.
        project_name: Name of the project for the entry point script.
        framework: UI framework name, or None.
        project_type: Project type name, or None.
        author_name: Author name for pyproject.toml authors field.
        author_email: Author email for pyproject.toml authors field.
        description: Project description for pyproject.toml.
        license_type: SPDX license identifier for pyproject.toml.
        imported_structure: If True, skip hatch/scripts config (imported layout).
    """
    pyproject_file = project_path / "pyproject.toml"

    # First, modify existing [project] section for metadata fields
    if author_name or author_email or description or license_type:
        content = pyproject_file.read_text(encoding="utf-8")
        content = _apply_metadata_to_pyproject(
            content, author_name, author_email, description, license_type
        )
        pyproject_file.write_text(content, encoding="utf-8")

    # Skip hatch build config and entry point for imported structures
    if imported_structure:
        return

    # Append hatch build config and entry point
    entry_point = _resolve_entry_point(framework, project_type)

    config = '\n[tool.hatch.build.targets.wheel]\npackages = ["app"]\n'
    if entry_point is not None:
        config += f'\n[project.scripts]\n{project_name} = "{entry_point}"\n'

    with open(pyproject_file, "a") as f:
        f.write(config)


def _replace_description(content: str, description: str) -> str:
    """Replace the description line in the [project] section."""
    lines = content.split("\n")
    result_lines = []
    in_project = False
    for line in lines:
        if line.strip() == "[project]":
            in_project = True
            result_lines.append(line)
            continue
        if in_project and line.strip().startswith("[") and line.strip() != "[project]":
            in_project = False
        if in_project and line.startswith("description"):
            result_lines.append(
                f'description = "{description}"' if description else line
            )
            continue
        result_lines.append(line)
    return "\n".join(result_lines)


def _insert_line_after_fields(
    content: str, new_line: str, after_fields: tuple[str, ...]
) -> str:
    """Insert new_line after the last line starting with any of after_fields."""
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith(after_fields):
            insert_idx = i + 1
    if insert_idx is not None:
        lines.insert(insert_idx, new_line)
    return "\n".join(lines)


def _apply_metadata_to_pyproject(
    content: str,
    author_name: str,
    author_email: str,
    description: str,
    license_type: str,
) -> str:
    """Apply metadata fields to pyproject.toml content.

    Performs targeted line replacements on the UV-generated pyproject.toml
    format, which has a predictable structure.

    Args:
        content: Current pyproject.toml content.
        author_name: Author name.
        author_email: Author email.
        description: Project description.
        license_type: SPDX license identifier.

    Returns:
        Modified pyproject.toml content.
    """
    content = _replace_description(content, description)

    if author_name or author_email:
        parts = []
        if author_name:
            parts.append(f'name = "{author_name}"')
        if author_email:
            parts.append(f'email = "{author_email}"')
        authors_line = "authors = [{" + ", ".join(parts) + "}]"
        content = _insert_line_after_fields(
            content, authors_line, ("description", "version")
        )

    if license_type:
        content = _insert_line_after_fields(
            content,
            f'license = "{license_type}"',
            ("authors", "description", "version"),
        )

    return content
