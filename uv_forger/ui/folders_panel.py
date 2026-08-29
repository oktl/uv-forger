"""Declarative project-structure panel.

Companion to :mod:`uv_forger.ui.packages_panel`, and the same hosting contract:
state arrives as a **getter**, not as the observable ``AppState``. Flet
subscribes a component to any ``Observable`` argument, whole-object, so passing
the state directly would mark this panel dirty on every unrelated write and the
next imperative ``page.update()`` would re-render it into fresh control ids
without patching the client — silently dropping every click. Handlers
re-render explicitly with ``controls.folders_panel.update()``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import flet as ft

from uv_forger.core.models import get_canonical_file_path
from uv_forger.ui.ui_config import UIConfig

if TYPE_CHECKING:
    from uv_forger.core.state import AppState

ItemPath = list[int | str]


def _noop(*_args: Any) -> None:
    """Placeholder used before attach_handlers() wires the real callbacks."""


@dataclass
class FolderPanelCallbacks:
    """Click callbacks for the folders panel.

    The panel is built before the handlers exist, so `build_main_view` creates
    one of these and `attach_handlers` fills in the fields. Identity stays
    stable, which is what `ft.memo` compares.

    Attributes:
        select: Called with (item_path, item_type, name) when an item is clicked.
        file_action: Called with (action, item_path, name) from a file's context menu.
        folder_action: Called with (action, item_path, name) from a folder's context menu.
    """

    select: Callable[[ItemPath, str, str], None] = field(default=_noop)
    file_action: Callable[[str, ItemPath, str], None] = field(default=_noop)
    folder_action: Callable[[str, ItemPath, str], None] = field(default=_noop)


_FILE_MENU: list[tuple[str, str, str]] = [
    ("preview", ft.Icons.PREVIEW, "Preview Content"),
    ("edit", ft.Icons.EDIT, "Edit Content..."),
    ("import", ft.Icons.FILE_OPEN, "Import from File..."),
    ("reset", ft.Icons.RESTART_ALT, "Reset to Default"),
]

_FOLDER_MENU: list[tuple[str, str, str]] = [
    ("import_folder", ft.Icons.CREATE_NEW_FOLDER, "Import Folder from Disk..."),
]


def _context_menu(
    content: ft.Control,
    items: list[tuple[str, str, str]],
    item_path: ItemPath,
    name: str,
    on_action: Callable[[str, ItemPath, str], None],
) -> ft.ContextMenu:
    """Wrap a control in a right-click menu whose entries dispatch `on_action`."""
    return ft.ContextMenu(
        content=content,
        secondary_items=[
            ft.PopupMenuItem(
                icon=icon,
                content=ft.Text(label),
                on_click=lambda _e, a=action: on_action(a, item_path, name),
            )
            for action, icon, label in items
        ],
    )


def _item_control(
    name: str,
    item_path: ItemPath,
    item_type: str,
    indent: int,
    state: AppState,
    callbacks: FolderPanelCallbacks,
) -> ft.Control:
    """Build one folder or file row, wrapped in its context menu.

    Files carry a pencil icon when they have a content override.
    """
    is_selected = (
        state.selected_item_path == item_path and state.selected_item_type == item_type
    )
    is_folder = item_type == "folder"

    row: list[ft.Control] = [
        ft.Icon(
            ft.Icons.FOLDER if is_folder else ft.Icons.INSERT_DRIVE_FILE,
            size=13,
            color=UIConfig.COLOR_FOLDER_ICON if is_folder else UIConfig.COLOR_FILE_ICON,
        ),
        ft.Text(
            f"{name}/" if is_folder else name,
            size=UIConfig.TEXT_SIZE_SMALL,
            font_family="monospace",
            color=None if is_folder else UIConfig.COLOR_FILE_TEXT,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        ),
    ]

    if not is_folder:
        canonical = get_canonical_file_path(
            state.folders, item_path, root_files=state.root_files
        )
        if canonical and canonical in state.file_overrides:
            row.append(ft.Icon(ft.Icons.EDIT_NOTE, size=10, color=UIConfig.COLOR_INFO))

    container = ft.Container(
        content=ft.Row(row, spacing=4, tight=True),
        bgcolor=UIConfig.SELECTED_ITEM_BGCOLOR if is_selected else None,
        border=ft.Border.all(
            UIConfig.BORDER_WIDTH_DEFAULT, UIConfig.SELECTED_ITEM_BORDER_COLOR
        )
        if is_selected
        else None,
        on_click=lambda _e: callbacks.select(item_path, item_type, name),
        padding=ft.Padding(
            left=4 + indent * UIConfig.FOLDER_TREE_INDENT_PX, right=4, top=1, bottom=1
        ),
        border_radius=2,
        margin=0,
    )

    if is_folder:
        return _context_menu(
            container, _FOLDER_MENU, item_path, name, callbacks.folder_action
        )
    return _context_menu(container, _FILE_MENU, item_path, name, callbacks.file_action)


def _folder_rows(
    folder: dict[str, Any],
    base_path: ItemPath,
    indent: int,
    state: AppState,
    callbacks: FolderPanelCallbacks,
) -> list[ft.Control]:
    """Flatten one folder — itself, then its files, then its subfolders."""
    rows = [
        _item_control(
            folder.get("name", ""), base_path, "folder", indent, state, callbacks
        )
    ]

    for file_idx, file_name in enumerate(folder.get("files", [])):
        rows.append(
            _item_control(
                file_name,
                base_path + ["files", file_idx],
                "file",
                indent + 1,
                state,
                callbacks,
            )
        )

    for sub_idx, subfolder in enumerate(folder.get("subfolders", [])):
        rows.extend(
            _folder_rows(
                subfolder,
                base_path + ["subfolders", sub_idx],
                indent + 1,
                state,
                callbacks,
            )
        )

    return rows


@ft.component
def FoldersPanel(
    get_state: Callable[[], AppState], callbacks: FolderPanelCallbacks
) -> ft.Control:
    """Bordered container showing the project structure tree.

    Args:
        get_state: Returns the application state. A getter, not the state
            itself — see the module docstring.
        callbacks: Click callbacks, filled in by `attach_handlers`.
    """
    state = get_state()
    rows: list[ft.Control] = []

    # Root-level files from an imported structure sit above the folders.
    if state.imported_structure and state.root_files:
        rows += [
            _item_control(name, ["root_files", idx], "file", 0, state, callbacks)
            for idx, name in enumerate(state.root_files)
        ]

    for idx, folder in enumerate(state.folders):
        rows += _folder_rows(folder, [idx], 0, state, callbacks)

    return ft.Container(
        content=ft.Column(controls=rows, spacing=0, scroll=ft.ScrollMode.AUTO),
        border=ft.Border.all(1, ft.Colors.GREY_700),
        border_radius=4,
        padding=10,
        height=UIConfig.SUBFOLDERS_HEIGHT,
        width=UIConfig.SPLIT_CONTAINER_WIDTH,
    )
