"""Handlers for folder tree display and management."""

import asyncio
from pathlib import Path
from typing import Any

import flet as ft

from uv_forger.core.validator import validate_folder_name
from uv_forger.ui.dialogs import create_add_item_dialog
from uv_forger.ui.ui_config import UIConfig

IMPORTABLE_EXTENSIONS: list[str] = [
    "py",
    "txt",
    "md",
    "json",
    "yaml",
    "yml",
    "toml",
    "cfg",
    "ini",
    "html",
    "css",
    "js",
    "ts",
]

_SKIP_DIRS: set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".env",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
}


def scan_folder_from_disk(
    folder_path: Path,
    *,
    max_files: int = 50,
    max_depth: int = 5,
) -> tuple[dict[str, Any], dict[str, str], dict[str, int]]:
    """Scan a directory from disk and return a folder structure with file contents.

    Args:
        folder_path: Path to the directory to scan.
        max_files: Maximum number of files to read content for.
        max_depth: Maximum recursion depth for subdirectories.

    Returns:
        Tuple of (folder_dict, file_overrides, stats):
        - folder_dict: Nested dict matching FolderSpec format.
        - file_overrides: Mapping of canonical paths to file contents.
        - stats: Counts of folders, files, and skipped items.
    """
    file_count = [0]
    stats: dict[str, int] = {"folders": 0, "files": 0, "skipped": 0}

    def _scan(path: Path, depth: int, prefix: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": path.name,
            "create_init": False,
            "subfolders": [],
            "files": [],
        }
        stats["folders"] += 1

        if depth >= max_depth:
            return result

        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return result

        for entry in entries:
            if entry.name.startswith("."):
                continue

            if entry.is_dir():
                if entry.name in _SKIP_DIRS:
                    continue
                child = _scan(entry, depth + 1, f"{prefix}{entry.name}/")
                result["subfolders"].append(child)

            elif entry.is_file():
                ext = entry.suffix.lstrip(".")
                if ext not in IMPORTABLE_EXTENSIONS:
                    stats["skipped"] += 1
                    continue

                if file_count[0] >= max_files:
                    stats["skipped"] += 1
                    continue

                try:
                    content = entry.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    stats["skipped"] += 1
                    continue

                result["files"].append(entry.name)
                file_overrides[f"{prefix}{entry.name}"] = content
                file_count[0] += 1
                stats["files"] += 1

        return result

    file_overrides: dict[str, str] = {}
    root = _scan(folder_path, 0, f"{folder_path.name}/")
    return root, file_overrides, stats


def get_canonical_file_path(
    folders: list[dict[str, Any]],
    item_path: list[int | str],
    root_files: list[str] | None = None,
) -> str | None:
    """Walk the folder tree by navigation path to build a canonical file path.

    Args:
        folders: Normalized folder list from state.
        item_path: Navigation path (e.g., [0, "files", 1] or [0, "subfolders", 0, "files", 2]).
        root_files: Optional list of root-level file names for imported structures.

    Returns:
        Canonical path string like "core/state.py", or None if path is invalid.
    """
    # Handle root_files paths (e.g., ["root_files", 0])
    if item_path and len(item_path) == 2 and item_path[0] == "root_files":
        idx = item_path[1]
        if root_files and isinstance(idx, int) and 0 <= idx < len(root_files):
            return root_files[idx]
        return None

    parts: list[str] = []
    current: Any = folders
    for segment in item_path:
        if isinstance(segment, int):
            try:
                current = current[segment]
            except (IndexError, KeyError, TypeError):
                return None
            # If this is a folder dict, record its name
            if isinstance(current, dict) and "name" in current:
                parts.append(current["name"])
            # If this is a string (a filename), record it
            elif isinstance(current, str):
                parts.append(current)
        elif segment == "subfolders":
            current = current.get("subfolders", []) if isinstance(current, dict) else []
        elif segment == "files":
            current = current.get("files", []) if isinstance(current, dict) else []
    return "/".join(parts) if parts else None


class FolderHandlersMixin:
    """Mixin for folder tree display, selection, add/remove operations.

    Expects HandlerBase helpers available via self.
    """

    def _create_item_container(
        self, name: str, item_path: list[int | str], item_type: str, indent: int = 0
    ) -> ft.Control:
        """Create a clickable container for a folder or file.

        For files, wraps the container in a ContextMenu with preview/edit/import/reset
        actions. Files with content overrides show a pencil icon indicator.

        Args:
            name: Display name of the item.
            item_path: Navigation path to the item.
            item_type: Either "folder" or "file".
            indent: Indentation level (0 = root).

        Returns:
            Configured Container (or ContextMenu wrapping one) with click handler.
        """
        is_selected = (
            self.state.selected_item_path == item_path
            and self.state.selected_item_type == item_type
        )

        if item_type == "folder":
            icon = ft.Icons.FOLDER
            icon_color = UIConfig.COLOR_FOLDER_ICON
            display_text = f"{name}/"
            text_color = None
        else:
            icon = ft.Icons.INSERT_DRIVE_FILE
            icon_color = UIConfig.COLOR_FILE_ICON
            display_text = name
            text_color = UIConfig.COLOR_FILE_TEXT

        row_controls = [
            ft.Icon(icon, size=13, color=icon_color),
            ft.Text(
                display_text,
                size=UIConfig.TEXT_SIZE_SMALL,
                font_family="monospace",
                color=text_color,
                overflow=ft.TextOverflow.ELLIPSIS,
                expand=True,
            ),
        ]

        # Show pencil icon for files with content overrides
        if item_type == "file":
            canonical = get_canonical_file_path(
                self.state.folders, item_path, root_files=self.state.root_files
            )
            if canonical and canonical in self.state.file_overrides:
                row_controls.append(
                    ft.Icon(ft.Icons.EDIT_NOTE, size=10, color=UIConfig.COLOR_INFO)
                )

        container = ft.Container(
            content=ft.Row(row_controls, spacing=4, tight=True),
            data={"path": item_path, "type": item_type, "name": name},
            bgcolor=UIConfig.SELECTED_ITEM_BGCOLOR if is_selected else None,
            border=(
                ft.Border.all(
                    UIConfig.BORDER_WIDTH_DEFAULT, UIConfig.SELECTED_ITEM_BORDER_COLOR
                )
                if is_selected
                else None
            ),
            on_click=self._on_item_click,
            padding=ft.Padding(
                left=4 + indent * UIConfig.FOLDER_TREE_INDENT_PX,
                right=4,
                top=1,
                bottom=1,
            ),
            border_radius=2,
            margin=0,
        )

        # Wrap file items in a context menu
        if item_type == "file":
            context_menu = ft.ContextMenu(
                content=container,
                secondary_items=[
                    ft.PopupMenuItem(
                        icon=ft.Icons.PREVIEW,
                        content=ft.Text("Preview Content"),
                        data={"action": "preview", "path": item_path, "name": name},
                        on_click=self._on_file_context_action,
                    ),
                    ft.PopupMenuItem(
                        icon=ft.Icons.EDIT,
                        content=ft.Text("Edit Content..."),
                        data={"action": "edit", "path": item_path, "name": name},
                        on_click=self._on_file_context_action,
                    ),
                    ft.PopupMenuItem(
                        icon=ft.Icons.FILE_OPEN,
                        content=ft.Text("Import from File..."),
                        data={"action": "import", "path": item_path, "name": name},
                        on_click=self._on_file_context_action,
                    ),
                    ft.PopupMenuItem(
                        icon=ft.Icons.RESTART_ALT,
                        content=ft.Text("Reset to Default"),
                        data={"action": "reset", "path": item_path, "name": name},
                        on_click=self._on_file_context_action,
                    ),
                ],
            )
            return context_menu

        # Wrap folder items in a context menu
        if item_type == "folder":
            context_menu = ft.ContextMenu(
                content=container,
                secondary_items=[
                    ft.PopupMenuItem(
                        icon=ft.Icons.CREATE_NEW_FOLDER,
                        content=ft.Text("Import Folder from Disk..."),
                        data={
                            "action": "import_folder",
                            "path": item_path,
                            "name": name,
                        },
                        on_click=self._on_folder_context_action,
                    ),
                ],
            )
            return context_menu

        return container

    def _process_folder_recursive(
        self,
        folder: dict[str, Any],
        base_path: list[int | str],
        indent: int,
        display_controls: list,
    ) -> None:
        """Recursively process a folder dict and add to display controls.

        Args:
            folder: Normalized folder dict with name, subfolders, files keys.
            base_path: Navigation path to this folder.
            indent: Current indentation level.
            display_controls: List to append created containers to.
        """
        name = folder.get("name", "")
        display_controls.append(
            self._create_item_container(name, base_path, "folder", indent)
        )

        for file_idx, file_name in enumerate(folder.get("files", [])):
            file_path = base_path + ["files", file_idx]
            display_controls.append(
                self._create_item_container(file_name, file_path, "file", indent + 1)
            )

        for subfolder_idx, subfolder in enumerate(folder.get("subfolders", [])):
            subfolder_path = base_path + ["subfolders", subfolder_idx]
            self._process_folder_recursive(
                subfolder, subfolder_path, indent + 1, display_controls
            )

    @staticmethod
    def _count_folders_and_files(folders: list[dict[str, Any]]) -> tuple[int, int]:
        """Recursively count folders and files in a normalized folder structure.

        Args:
            folders: List of normalized folder dicts.

        Returns:
            Tuple of (folder_count, file_count).
        """
        folder_count = 0
        file_count = 0

        for folder in folders:
            folder_count += 1
            if folder.get("create_init", True):
                file_count += 1  # __init__.py
            file_count += len(folder.get("files", []) or [])
            subfolders = folder.get("subfolders", []) or []
            if subfolders:
                sub_f, sub_fi = FolderHandlersMixin._count_folders_and_files(subfolders)
                folder_count += sub_f
                file_count += sub_fi

        return folder_count, file_count

    def _update_folder_display(self) -> None:
        """Update the folder display container with current folder structure."""
        folder_controls = []

        # Show root-level files from imported structure before folders
        if self.state.imported_structure and self.state.root_files:
            for rf_idx, rf_name in enumerate(self.state.root_files):
                rf_path = ["root_files", rf_idx]
                folder_controls.append(
                    self._create_item_container(rf_name, rf_path, "file", indent=0)
                )

        for idx, folder in enumerate(self.state.folders):
            self._process_folder_recursive(folder, [idx], 0, folder_controls)

        self.controls.subfolders_container.content.controls = folder_controls

        folder_count, file_count = self._count_folders_and_files(self.state.folders)
        if self.state.imported_structure:
            total_files = file_count + len(self.state.root_files)
            label = f"Project Structure: {folder_count} folders, {total_files} files"
        else:
            label = f"App Subfolders: {folder_count} folders, {file_count} files"
        self.controls.app_subfolders_label.value = label

        self._update_preset_button_state()
        self.page.update()

    def _on_item_click(self, e: ft.ControlEvent) -> None:
        """Handle click on folder/file item to select it."""
        self.state.selected_item_path = e.control.data["path"]
        self.state.selected_item_type = e.control.data["type"]
        item_name = e.control.data["name"]
        self._set_status(
            f"Selected {e.control.data['type']}: {item_name}", "info", update=False
        )
        # Enable/disable edit file button based on whether a file is selected
        if hasattr(self.controls, "edit_file_button"):
            is_file = e.control.data["type"] == "file"
            self.controls.edit_file_button.disabled = not is_file
        self._update_folder_display()

    def _get_folder_hierarchy(self) -> list[dict]:
        """Build list of all folders with their paths for parent selection.

        Returns:
            List of dicts with "label" (display name) and "path" (navigation path).
        """
        hierarchy = []

        def process_folder(
            folder: dict[str, Any], base_path: list, parent_name: str = ""
        ) -> None:
            name = folder.get("name", "")
            label = f"{parent_name}{name}/" if parent_name else f"{name}/"
            hierarchy.append({"label": label, "path": base_path})

            for subfolder_idx, subfolder in enumerate(folder.get("subfolders", [])):
                subfolder_path = base_path + ["subfolders", subfolder_idx]
                process_folder(subfolder, subfolder_path, label)

        for idx, folder in enumerate(self.state.folders):
            process_folder(folder, [idx])

        return hierarchy

    def _navigate_to_parent(
        self, path: list | None
    ) -> tuple[list | dict, int | str | None]:
        """Navigate to parent container by path.

        Args:
            path: Path to navigate (e.g., [0, "subfolders", 1])

        Returns:
            Tuple of (parent_container, index).
        """
        if not path:
            return self.state.folders, None

        # Handle root_files paths (e.g., ["root_files", 0])
        if path[0] == "root_files":
            return self.state.root_files, path[-1]

        current = self.state.folders
        for segment in path[:-1]:
            if isinstance(segment, int):
                current = current[segment]
            elif segment == "subfolders":
                current = current.get("subfolders", [])
            elif segment == "files":
                current = current.get("files", [])

        return current, path[-1]

    async def on_add_folder(self, e: ft.ControlEvent) -> None:
        """Handle Add Folder button click.

        Opens dialog to add a folder or file at a selected location.
        """

        async def add_item(
            name: str,
            item_type: str,
            parent_path: list | None,
            content: str | tuple | None = None,
        ):
            """Add folder or file to state."""
            valid, error = validate_folder_name(name)
            if not valid:
                dialog.warning_text.value = error
                dialog.warning_text.visible = True
                self.page.update()
                return

            if parent_path is None:
                parent_container = self.state.folders
            else:
                parent_container, idx = self._navigate_to_parent(parent_path)
                if isinstance(idx, int):
                    parent_folder = parent_container[idx]
                elif idx == "subfolders":
                    parent_folder = parent_container
                elif idx == "files":
                    dialog.warning_text.value = "Cannot add items inside a file."
                    dialog.warning_text.visible = True
                    self.page.update()
                    return
                else:
                    parent_folder = parent_container

                if item_type == "folder":
                    parent_container = parent_folder.setdefault("subfolders", [])
                else:
                    parent_container = parent_folder.setdefault("files", [])

            if item_type == "folder":
                # Check if content is an imported folder (tuple of dict, overrides)
                if isinstance(content, tuple):
                    folder_dict, file_overrides = content
                    new_item = folder_dict
                    new_item["name"] = name  # Use user-edited name
                else:
                    new_item = {"name": name, "subfolders": [], "files": []}

                if parent_path is None:
                    self.state.folders.append(new_item)
                else:
                    parent_container.append(new_item)

                # Merge file_overrides for imported folders
                if isinstance(content, tuple):
                    _, file_overrides = content
                    # Build canonical prefix for insertion point
                    if parent_path is not None:
                        parent_canonical = get_canonical_file_path(
                            self.state.folders,
                            parent_path,
                            root_files=self.state.root_files,
                        )
                        prefix = f"{parent_canonical}/" if parent_canonical else ""
                    else:
                        prefix = ""
                    # file_overrides keys are like "origname/sub/file.py"
                    # Replace the original folder name prefix with the user name
                    for rel_path, file_content in file_overrides.items():
                        # rel_path starts with "original_name/..."
                        parts = rel_path.split("/", 1)
                        if len(parts) == 2:
                            adjusted = f"{name}/{parts[1]}"
                        else:
                            adjusted = rel_path
                        self.state.file_overrides[f"{prefix}{adjusted}"] = file_content
            else:
                if parent_path is None:
                    dialog.warning_text.value = "Files must be added inside a folder."
                    dialog.warning_text.visible = True
                    self.page.update()
                    return
                parent_container.append(name)

                # Store imported content in file_overrides if provided
                if content is not None:
                    file_idx = len(parent_container) - 1
                    file_path = parent_path + ["files", file_idx]
                    canonical = get_canonical_file_path(
                        self.state.folders,
                        file_path,
                        root_files=self.state.root_files,
                    )
                    if canonical:
                        self.state.file_overrides[canonical] = content

            self.state.folders_modified = True
            self._update_folder_display()

            dialog.warning_text.value = ""
            dialog.warning_text.visible = False
            dialog.open = False
            self.state.active_dialog = None

            status = f"{item_type.title()} '{name}' added."
            if isinstance(content, tuple):
                status = f"Folder '{name}' imported from disk."
            elif content is not None:
                status = f"File '{name}' added with imported content."
            self._set_status(status, "success", update=True)

        async def browse_file(name_field, imported_content, browse_feedback):
            """Open file picker and populate dialog fields with selected file."""
            files = await ft.FilePicker().pick_files(
                dialog_title="Select file to import",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=IMPORTABLE_EXTENSIONS,
                allow_multiple=False,
            )
            if files:
                picked = files[0]
                try:
                    picked_path = Path(picked.path)
                    content = picked_path.read_text(encoding="utf-8")
                    imported_content[0] = content
                    # Auto-fill name field with picked filename
                    name_field.value = picked.name
                    browse_feedback.value = picked.name
                    browse_feedback.visible = True
                    self.page.update()
                except (OSError, UnicodeDecodeError) as exc:
                    imported_content[0] = None
                    browse_feedback.value = f"Error: {exc}"
                    browse_feedback.visible = True
                    self.page.update()

        async def browse_folder(name_field, imported_folder_data, browse_feedback):
            """Open directory picker and scan folder for import."""
            result = await ft.FilePicker().get_directory_path(
                dialog_title="Select folder to import",
            )
            if not result:
                return

            folder_path = Path(result)
            folder_dict, file_overrides, stats = scan_folder_from_disk(folder_path)

            if stats["files"] == 0 and stats["folders"] <= 1:
                browse_feedback.value = "Folder is empty or has no importable files"
                browse_feedback.visible = True
                self.page.update()
                return

            imported_folder_data[0] = (folder_dict, file_overrides)
            name_field.value = folder_path.name
            summary = f"{stats['folders']} folders, {stats['files']} files"
            if stats["skipped"] > 0:
                summary += f", {stats['skipped']} skipped"
            browse_feedback.value = summary
            browse_feedback.visible = True
            self.page.update()

        def close_dialog(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        parent_folders = self._get_folder_hierarchy()

        dialog = create_add_item_dialog(
            lambda n, t, p, c: asyncio.create_task(add_item(n, t, p, c)),
            close_dialog,
            parent_folders,
            self.state.is_dark_mode,
            on_browse_callback=browse_file,
            on_browse_folder_callback=browse_folder,
        )

        self._set_warning("", update=False)

        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    async def on_remove_folder(self, e: ft.ControlEvent) -> None:
        """Handle Remove Folder button click.

        Removes the currently selected folder or file from state.
        """
        if not self.state.selected_item_path:
            self._set_status(
                "No item selected. Click an item to select it first.",
                "info",
                update=True,
            )
            return

        parent_container, idx = self._navigate_to_parent(self.state.selected_item_path)

        if parent_container is None or idx is None:
            self._set_warning("Cannot remove item: invalid selection.", update=True)
            return

        item_type = self.state.selected_item_type
        if isinstance(idx, int) and idx < len(parent_container):
            item = parent_container[idx]
            item_name = item.get("name", "unnamed") if isinstance(item, dict) else item

            # Clean up file_overrides for removed root files
            if (
                isinstance(item, str)
                and self.state.selected_item_path
                and (self.state.selected_item_path[0] == "root_files")
            ):
                self.state.file_overrides.pop(item, None)

            del parent_container[idx]

            self.state.selected_item_path = None
            self.state.selected_item_type = None

            self.state.folders_modified = True
            self._update_folder_display()
            self._set_status(
                f"{item_type.title()} '{item_name}' removed.", "success", update=True
            )
        else:
            self._set_warning("Cannot remove item: index out of range.", update=True)

    # ---- File content editing (context menu + button) ----

    def _get_file_boilerplate(self, filename: str) -> str | None:
        """Resolve boilerplate content for a filename using current config.

        Args:
            filename: The file name (e.g., "main.py").

        Returns:
            Boilerplate content string, or None if no boilerplate available.
        """
        from uv_forger.core.boilerplate_resolver import BoilerplateResolver
        from uv_forger.core.settings_manager import get_user_templates_dir

        if not self.state.include_starter_files:
            return None
        try:
            resolver = BoilerplateResolver(
                project_name=self.state.project_name or "my_project",
                framework=self.state.framework
                if self.state.ui_project_enabled
                else None,
                project_type=self.state.project_type
                if self.state.other_project_enabled
                else None,
                user_boilerplate_dir=get_user_templates_dir(self.state.settings)
                / "boilerplate",
            )
            return resolver.resolve(filename)
        except ValueError:
            return None

    def _get_user_template_path(self, filename: str) -> Path:
        """Compute the user template file path for the current framework/project type.

        Args:
            filename: The file name (e.g., "main.py").

        Returns:
            Path where the user template file would be stored.
        """
        from uv_forger.core.boilerplate_resolver import normalize_framework_name
        from uv_forger.core.settings_manager import get_user_templates_dir

        user_dir = get_user_templates_dir(self.state.settings) / "boilerplate"
        if self.state.ui_project_enabled and self.state.framework:
            normalized = normalize_framework_name(self.state.framework)
            return user_dir / "ui_frameworks" / normalized / filename
        elif self.state.other_project_enabled and self.state.project_type:
            return user_dir / "project_types" / self.state.project_type / filename
        return user_dir / "common" / filename

    def _user_template_exists(self, filename: str) -> bool:
        """Check if a user template file exists for this filename.

        Args:
            filename: The file name (e.g., "main.py").

        Returns:
            True if a user template file exists at the computed path.
        """
        return self._get_user_template_path(filename).is_file()

    def _delete_user_template_file(self, filename: str) -> bool:
        """Remove a user template file.

        Args:
            filename: The file name (e.g., "main.py").

        Returns:
            True if the file was deleted, False if it didn't exist.
        """
        path = self._get_user_template_path(filename)
        if path.is_file():
            path.unlink()
            return True
        return False

    def _on_folder_context_action(self, e: ft.ControlEvent) -> None:
        """Dispatch folder context menu actions."""
        data = e.control.data
        action = data["action"]
        item_path = data["path"]

        if action == "import_folder":
            asyncio.create_task(self._import_folder_from_disk(parent_path=item_path))

    async def _import_folder_from_disk(
        self, parent_path: list[int | str] | None
    ) -> None:
        """Import an entire directory from disk into the folder tree.

        Args:
            parent_path: Navigation path to the parent folder where the imported
                folder will be inserted as a subfolder. None for root level.
        """
        result = await ft.FilePicker().get_directory_path(
            dialog_title="Select folder to import",
        )
        if not result:
            return

        folder_dict, file_overrides, stats = scan_folder_from_disk(Path(result))

        if stats["files"] == 0 and stats["folders"] <= 1:
            self._set_status(
                "Selected folder is empty or has no importable files.",
                "info",
                update=True,
            )
            return

        # Insert the folder into the tree
        if parent_path is None:
            self.state.folders.append(folder_dict)
        else:
            parent_container, idx = self._navigate_to_parent(parent_path)
            if isinstance(idx, int):
                parent_folder = parent_container[idx]
            else:
                parent_folder = parent_container
            parent_folder.setdefault("subfolders", []).append(folder_dict)

        # Compute canonical prefix for file_overrides
        # Build the prefix by walking the parent path
        if parent_path is not None:
            parent_canonical = get_canonical_file_path(
                self.state.folders, parent_path, root_files=self.state.root_files
            )
            if parent_canonical:
                prefix = f"{parent_canonical}/"
            else:
                prefix = ""
        else:
            prefix = ""

        for rel_path, content in file_overrides.items():
            self.state.file_overrides[f"{prefix}{rel_path}"] = content

        self._update_folder_display()

        status = f"Imported '{folder_dict['name']}' ({stats['folders']} folders, {stats['files']} files)"
        if stats["skipped"] > 0:
            status += f", {stats['skipped']} skipped"
        self._set_status(status, "success", update=True)

    def _on_file_context_action(self, e: ft.ControlEvent) -> None:
        """Dispatch context menu actions to the appropriate handler."""
        data = e.control.data
        action = data["action"]
        item_path = data["path"]
        name = data["name"]

        if action == "preview":
            asyncio.create_task(self._preview_file(item_path, name))
        elif action == "edit":
            asyncio.create_task(self._edit_file(item_path, name))
        elif action == "import":
            asyncio.create_task(self._import_file(item_path, name))
        elif action == "reset":
            self._reset_file_override(item_path, name)

    async def on_edit_file(self, e: ft.ControlEvent) -> None:
        """Handle Edit File button click — edits the currently selected file."""
        if not self.state.selected_item_path or self.state.selected_item_type != "file":
            self._set_status("Select a file in the tree first.", "info", update=True)
            return

        # Find the filename from the last segment of the path
        parent, idx = self._navigate_to_parent(self.state.selected_item_path)
        if isinstance(idx, int) and isinstance(parent, list) and idx < len(parent):
            filename = parent[idx] if isinstance(parent[idx], str) else "unknown"
        else:
            return

        await self._edit_file(self.state.selected_item_path, filename)

    async def _preview_file(self, item_path: list[int | str], filename: str) -> None:
        """Show a read-only preview of file content."""
        from uv_forger.ui.content_dialogs import create_file_preview_dialog

        canonical = get_canonical_file_path(
            self.state.folders, item_path, root_files=self.state.root_files
        )
        if not canonical:
            return

        # Get content: override first, then boilerplate, then empty
        if canonical in self.state.file_overrides:
            content = self.state.file_overrides[canonical]
            source = "Custom content (edited)"
        else:
            content = self._get_file_boilerplate(filename)
            if content is not None:
                source = "From boilerplate"
            else:
                content = ""
                source = "Empty file (no boilerplate available)"

        def close_dialog(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_file_preview_dialog(
            filename=filename,
            content=content,
            source_label=source,
            on_close=close_dialog,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    async def _edit_file(self, item_path: list[int | str], filename: str) -> None:
        """Open the editor view for a file."""
        from uv_forger.ui.dialogs import create_file_editor_view

        canonical = get_canonical_file_path(
            self.state.folders, item_path, root_files=self.state.root_files
        )
        if not canonical:
            return

        # Get initial content: override first, then boilerplate, then empty
        if canonical in self.state.file_overrides:
            initial_content = self.state.file_overrides[canonical]
        else:
            initial_content = self._get_file_boilerplate(filename) or ""

        has_user_template = self._user_template_exists(filename)

        def close_editor():
            if len(self.page.views) > 1:
                self.page.views.pop()
            self.state.active_dialog = None
            self.page.update()

        def on_save(content: str):
            self.state.file_overrides[canonical] = content
            self.state.folders_modified = True
            close_editor()
            self._update_folder_display()
            self._set_status(f"Saved content for {filename}", "success", update=True)

        def on_reset_to_default():
            if has_user_template:
                self._do_reset_with_user_template_confirm(None, canonical, filename)
            else:
                self.state.file_overrides.pop(canonical, None)
                close_editor()
                self._update_folder_display()
                self._set_status(f"Reset {filename} to default", "info", update=True)

        # Compute user template path for the editor's built-in Save
        user_template_path = self._get_user_template_path(filename)
        user_template_path.parent.mkdir(parents=True, exist_ok=True)

        view = create_file_editor_view(
            filename=filename,
            initial_content=initial_content,
            on_save=on_save,
            on_reset=on_reset_to_default,
            on_close=close_editor,
            is_dark_mode=self.state.is_dark_mode,
            has_override=canonical in self.state.file_overrides,
            has_user_template=has_user_template,
            user_template_path=str(user_template_path),
        )

        self.page.editor_view_ref = view
        self.page.views.append(view)
        self.state.active_dialog = close_editor
        self.page.update()

    def _do_reset_with_user_template_confirm(
        self, _editor_dialog, canonical: str, filename: str
    ) -> None:
        """Show confirmation before deleting a user template file on Reset.

        Args:
            _editor_dialog: Unused (kept for API compat). Previously the dialog to close.
            canonical: Canonical file path key in file_overrides.
            filename: The file name being reset.
        """
        from uv_forger.ui.dialogs import create_confirm_dialog

        def on_confirm(_):
            self._delete_user_template_file(filename)
            self.state.file_overrides.pop(canonical, None)
            confirm_dialog.open = False
            # Close the editor view
            if len(self.page.views) > 1:
                self.page.views.pop()
            self.state.active_dialog = None
            self._update_folder_display()
            self._set_status(
                f"Deleted user template and reset {filename}", "info", update=True
            )

        def on_cancel(_=None):
            confirm_dialog.open = False
            self.page.update()

        confirm_dialog = create_confirm_dialog(
            title="Delete Custom Template?",
            message=(
                f"This will permanently delete your custom template for "
                f"'{filename}' and fall back to the bundled default."
            ),
            confirm_label="Delete",
            on_confirm=on_confirm,
            on_cancel=on_cancel,
            is_dark_mode=self.state.is_dark_mode,
            confirm_icon=ft.Icons.DELETE_FOREVER,
        )
        self.page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        self.page.update()

    async def _import_file(self, item_path: list[int | str], filename: str) -> None:
        """Import content from a local file into this project file."""
        canonical = get_canonical_file_path(
            self.state.folders, item_path, root_files=self.state.root_files
        )
        if not canonical:
            return

        files = await ft.FilePicker().pick_files(
            dialog_title=f"Import content for {filename}",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=IMPORTABLE_EXTENSIONS,
            allow_multiple=False,
        )
        if files:
            try:
                content = Path(files[0].path).read_text(encoding="utf-8")
                self.state.file_overrides[canonical] = content
                self._update_folder_display()
                self._set_status(
                    f"Imported content for {filename}", "success", update=True
                )
            except (OSError, UnicodeDecodeError) as exc:
                self._set_status(f"Import failed: {exc}", "error", update=True)

    def _reset_file_override(self, item_path: list[int | str], filename: str) -> None:
        """Remove any content override for a file."""
        canonical = get_canonical_file_path(
            self.state.folders, item_path, root_files=self.state.root_files
        )
        if canonical and canonical in self.state.file_overrides:
            del self.state.file_overrides[canonical]
            self._update_folder_display()
            self._set_status(f"Reset {filename} to default", "info", update=True)

    async def on_import_tree(self, e: ft.ControlEvent) -> None:
        """Handle Import Tree button click. Opens paste-tree dialog."""
        from uv_forger.core.template_merger import merge_folder_lists
        from uv_forger.ui.dialogs import create_import_tree_dialog

        def close_dialog(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def on_import(folders: list[dict], root_files: list[str], mode: str):
            if mode == "merge":
                self.state.folders = merge_folder_lists(self.state.folders, folders)
                # Merge root files (deduplicate)
                existing = set(self.state.root_files)
                for rf in root_files:
                    if rf not in existing:
                        self.state.root_files.append(rf)
            else:
                self.state.folders = folders
                self.state.root_files = list(root_files)
            self.state.folders_modified = True
            self.state.imported_structure = True
            close_dialog()
            self._update_folder_display()
            folder_count = len(folders)
            root_file_count = len(self.state.root_files)
            parts = [
                f"{folder_count} folder{'s' if folder_count != 1 else ''}",
            ]
            if root_file_count:
                parts.append(
                    f"{root_file_count} root file{'s' if root_file_count != 1 else ''}"
                )
            self._set_status(
                f"Imported {', '.join(parts)} ({mode}).",
                "success",
                update=True,
            )

        dialog = create_import_tree_dialog(
            on_import_callback=on_import,
            on_close_callback=close_dialog,
            is_dark_mode=self.state.is_dark_mode,
        )
        self.state.active_dialog = close_dialog
        self.page.show_dialog(dialog)

    async def on_clear_folders(self, e: ft.ControlEvent) -> None:
        """Handle Clear Folders button click. Confirms then clears all folders."""
        from uv_forger.ui.dialogs import create_confirm_dialog

        def close_dialog(_=None):
            confirm_dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def do_clear(_=None):
            self.state.folders = []
            self.state.file_overrides.clear()
            self.state.folders_modified = True
            self.state.imported_structure = False
            self.state.root_files = []
            close_dialog()
            self._update_folder_display()
            self._set_status("Folders cleared.", "info", update=True)

        if not self.state.folders:
            self._set_status("No folders to clear.", "info", update=True)
            return

        confirm_dialog = create_confirm_dialog(
            title="Clear All Folders?",
            message="This will remove all folders and files from the subfolders display.",
            confirm_label="Clear",
            on_confirm=do_clear,
            on_cancel=close_dialog,
            is_dark_mode=self.state.is_dark_mode,
            confirm_icon=ft.Icons.DELETE_SWEEP,
        )
        self.state.active_dialog = close_dialog
        self.page.show_dialog(confirm_dialog)
