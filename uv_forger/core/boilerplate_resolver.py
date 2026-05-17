"""Boilerplate file resolver for project scaffolding.

Looks up starter content for files created during project scaffolding.
Uses a fallback chain: framework-specific → project-type-specific → common → None.
"""

from pathlib import Path

from uv_forger.core.constants import BOILERPLATE_DIR


def normalize_project_name(project_name: str) -> str:
    """Convert dash/underscore-separated project name to title case with spaces.

    Args:
        project_name: Project name with dashes or underscores
                        e.g., "create-a-project", "my_app").

    Returns:
        Title-cased name with spaces (e.g., "Create A Project", "My App").
    """
    if not project_name:
        return ""

    # Replace both dashes and underscores with spaces
    normalized = project_name.replace("-", " ").replace("_", " ")
    # Title case each word
    return normalized.title()


def normalize_framework_name(framework: str) -> str:
    """Convert framework display name to a normalized directory/file name.

    Args:
        framework: Framework display name (e.g., "PyQt6", "tkinter (built-in)").

    Returns:
        Normalized name (e.g., "pyqt6", "tkinter").
    """
    name = framework.lower()
    name = name.replace(" (built-in)", "")
    name = name.replace(" ", "_")
    return name


class BoilerplateResolver:
    """Resolves filenames to boilerplate content using a fallback chain.

    Fallback order:
        1. boilerplate/ui_frameworks/{framework}/{filename}
        2. boilerplate/project_types/{project_type}/{filename}
        3. boilerplate/common/{filename}
        4. None (caller falls back to empty .touch())

    Attributes:
        project_name: Name of the project being created (used for placeholder substitution).
        search_dirs: Ordered list of directories to search for boilerplate files.

    Args:
        project_name: Name of the project being created (used for placeholder substitution).
        framework: Optional UI framework name (display name, will be normalized).
        project_type: Optional project type key (e.g., "django", "fastapi").
        boilerplate_dir: Optional override for the boilerplate directory (for testing).
        user_boilerplate_dir: Optional path to user boilerplate overlay directory
            (takes precedence over bundled boilerplate).
    """

    def __init__(
        self,
        project_name: str,
        framework: str | None = None,
        project_type: str | None = None,
        boilerplate_dir: Path | None = None,
        user_boilerplate_dir: Path | None = None,
    ):
        if not project_name:
            raise ValueError("project_name cannot be empty")

        self.project_name = project_name
        base = boilerplate_dir or BOILERPLATE_DIR

        self.search_dirs: list[Path] = []

        # User overlay dirs first (highest priority)
        if user_boilerplate_dir:
            if framework:
                normalized = normalize_framework_name(framework)
                self.search_dirs.append(
                    user_boilerplate_dir / "ui_frameworks" / normalized
                )
            if project_type:
                self.search_dirs.append(
                    user_boilerplate_dir / "project_types" / project_type
                )
            self.search_dirs.append(user_boilerplate_dir / "common")

        # Bundled dirs (existing behavior)
        if framework:
            normalized = normalize_framework_name(framework)
            self.search_dirs.append(base / "ui_frameworks" / normalized)
        if project_type:
            self.search_dirs.append(base / "project_types" / project_type)
        self.search_dirs.append(base / "common")

    def resolve(self, filename: str) -> str | None:
        """Look up boilerplate content for a filename.

        Searches the fallback chain in order and returns the first match,
        with ``{{project_name}}`` placeholders substituted.

        Args:
            filename: The file name to look up (e.g., "main.py", "state.py").

        Returns:
            File content string with placeholders replaced, or None if no
            boilerplate exists for this filename.
        """
        for directory in self.search_dirs:
            candidate = directory / filename
            if candidate.is_file():
                content = candidate.read_text(encoding="utf-8")
                return self._substitute(content)
        return None

    def _substitute(self, content: str) -> str:
        return content.replace(
            "{{project_name}}", normalize_project_name(self.project_name)
        )
