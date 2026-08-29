"""Tests for the declarative folders panel and how it is hosted."""

import flet as ft
from flet.components.observable import Observable

from uv_forger.core.state import AppState
from uv_forger.ui.components import Controls, render_folders_panel
from uv_forger.ui.folders_panel import FolderPanelCallbacks, FoldersPanel


def _rows(state: AppState, callbacks: FolderPanelCallbacks | None = None):
    """Render the panel body and return its row controls."""
    panel = FoldersPanel.__wrapped__(lambda: state, callbacks or FolderPanelCallbacks())
    return panel.content.controls


def _state(**kwargs) -> AppState:
    state = AppState()
    for key, value in kwargs.items():
        setattr(state, key, value)
    return state


# ---- tree flattening ----


def test_flat_folders_render_one_row_each():
    state = _state(
        folders=[
            {"name": "core", "subfolders": [], "files": []},
            {"name": "ui", "subfolders": [], "files": []},
            {"name": "utils", "subfolders": [], "files": []},
        ]
    )

    assert len(_rows(state)) == 3


def test_empty_folders_render_nothing():
    assert _rows(_state(folders=[])) == []


def test_nested_folders_are_flattened_depth_first():
    state = _state(
        folders=[
            {
                "name": "app",
                "files": ["main.py"],
                "subfolders": [
                    {"name": "core", "subfolders": [], "files": ["state.py"]}
                ],
            }
        ]
    )

    # app, main.py, core, state.py — folder, its files, then its subfolders
    labels = [row.content.content.controls[1].value for row in _rows(state)]
    assert labels == ["app/", "main.py", "core/", "state.py"]


def test_root_files_render_above_folders_when_imported():
    state = _state(
        imported_structure=True,
        root_files=["README.md", "pyproject.toml"],
        folders=[{"name": "src", "subfolders": [], "files": []}],
    )

    labels = [row.content.content.controls[1].value for row in _rows(state)]
    assert labels == ["README.md", "pyproject.toml", "src/"]


def test_root_files_hidden_when_structure_not_imported():
    state = _state(imported_structure=False, root_files=["README.md"], folders=[])

    assert _rows(state) == []


# ---- selection and indicators ----


def test_selected_item_is_highlighted():
    state = _state(
        folders=[{"name": "core", "subfolders": [], "files": []}],
        selected_item_path=[0],
        selected_item_type="folder",
    )

    container = _rows(state)[0].content
    assert container.bgcolor is not None
    assert container.border is not None


def test_unselected_item_is_not_highlighted():
    state = _state(
        folders=[{"name": "core", "subfolders": [], "files": []}],
        selected_item_path=[1],
        selected_item_type="folder",
    )

    container = _rows(state)[0].content
    assert container.bgcolor is None
    assert container.border is None


def test_matching_path_with_wrong_type_is_not_highlighted():
    state = _state(
        folders=[{"name": "core", "subfolders": [], "files": []}],
        selected_item_path=[0],
        selected_item_type="file",
    )

    assert _rows(state)[0].content.bgcolor is None


def test_pencil_icon_marks_files_with_an_override():
    state = _state(
        folders=[{"name": "core", "subfolders": [], "files": ["main.py"]}],
        file_overrides={"core/main.py": "# custom"},
    )

    row_controls = _rows(state)[1].content.content.controls
    assert len(row_controls) == 3  # icon, text, pencil
    assert row_controls[2].icon == ft.Icons.EDIT_NOTE


def test_no_pencil_icon_without_an_override():
    state = _state(
        folders=[{"name": "core", "subfolders": [], "files": ["main.py"]}],
        file_overrides={},
    )

    assert len(_rows(state)[1].content.content.controls) == 2


# ---- context menus ----


def test_folder_context_menu_offers_import_from_disk():
    state = _state(folders=[{"name": "core", "subfolders": [], "files": []}])

    row = _rows(state)[0]
    assert isinstance(row, ft.ContextMenu)
    assert [item.content.value for item in row.secondary_items] == [
        "Import Folder from Disk..."
    ]


def test_file_context_menu_offers_all_four_actions():
    state = _state(folders=[{"name": "core", "subfolders": [], "files": ["main.py"]}])

    row = _rows(state)[1]
    assert isinstance(row, ft.ContextMenu)
    assert [item.content.value for item in row.secondary_items] == [
        "Preview Content",
        "Edit Content...",
        "Import from File...",
        "Reset to Default",
    ]


# ---- dispatch ----


def test_row_click_dispatches_path_type_and_name():
    state = _state(folders=[{"name": "core", "subfolders": [], "files": ["main.py"]}])
    seen = []
    callbacks = FolderPanelCallbacks(select=lambda *args: seen.append(args))

    _rows(state, callbacks)[1].content.on_click(None)

    assert seen == [([0, "files", 0], "file", "main.py")]


def test_file_menu_items_dispatch_their_own_action():
    state = _state(folders=[{"name": "core", "subfolders": [], "files": ["main.py"]}])
    seen = []
    callbacks = FolderPanelCallbacks(file_action=lambda *args: seen.append(args))

    for item in _rows(state, callbacks)[1].secondary_items:
        item.on_click(None)

    assert [action for action, _path, _name in seen] == [
        "preview",
        "edit",
        "import",
        "reset",
    ]
    assert all(args[1:] == ([0, "files", 0], "main.py") for args in seen)


def test_folder_menu_item_dispatches_import_folder():
    state = _state(folders=[{"name": "core", "subfolders": [], "files": []}])
    seen = []
    callbacks = FolderPanelCallbacks(folder_action=lambda *args: seen.append(args))

    _rows(state, callbacks)[0].secondary_items[0].on_click(None)

    assert seen == [("import_folder", [0], "core")]


def test_callbacks_default_to_noops():
    """The panel is built before attach_handlers wires it; clicks must not blow up."""
    state = _state(folders=[{"name": "core", "subfolders": [], "files": ["main.py"]}])

    rows = _rows(state)
    rows[0].content.on_click(None)
    rows[0].secondary_items[0].on_click(None)
    rows[1].secondary_items[0].on_click(None)


# ---- hosting invariants (see packages_panel for the full rationale) ----


def _panel():
    state = AppState()
    controls = Controls()
    return state, controls, render_folders_panel(state, controls)


def test_panel_component_is_memoized():
    """Without memo, any imperative page.update() re-renders the panel into
    controls with new ids the client was never told about, and every click
    inside the panel is silently dropped."""
    _state_, _controls, panel = _panel()

    assert panel.memoized is True


def test_panel_is_not_subscribed_to_app_state():
    """Passing the observable AppState would mark the panel dirty on every
    unrelated state write, and the next imperative page.update() would then
    re-render it without patching the client."""
    _state_, _controls, panel = _panel()

    args = list(panel.args) + list(panel.kwargs.values())
    assert args, "panel is expected to take arguments"
    assert not any(isinstance(a, Observable) for a in args)


def test_panel_shares_the_callbacks_object_controls_holds():
    """attach_handlers fills in the same instance the panel rendered with."""
    _state_, controls, panel = _panel()

    assert controls.folder_callbacks in panel.args
