"""Tests for file content editing integration (context menu, overrides, canonical paths)."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import flet as ft
import pytest

from uv_forger.core.state import AppState
from uv_forger.handlers.folder_handlers import get_canonical_file_path
from uv_forger.handlers.ui_handler import Handlers


# --- Reuse mock classes from test_ui_handler ---
class MockControl:
    def __init__(self, value=None, label=None):
        self.value = value
        self.label = label
        self.label_style = None
        self.visible = True
        self.disabled = False
        self.color = None
        self.suffix = None
        self.opacity = 1.0
        self.tooltip = None

    async def focus(self):
        pass


class MockContainer:
    def __init__(self):
        self.content = Mock()
        self.content.controls = []
        self.border = None


class MockText:
    def __init__(self, value=""):
        self.value = value
        self.color = None


class MockPage:
    def __init__(self):
        self.updated = False
        self.overlay = []
        self.appbar = None
        self.bottom_appbar = Mock()
        self.bottom_appbar.bgcolor = None
        self.theme_mode = None
        self.window = Mock()
        self.opened_controls = []
        self.title = "UV Forger"
        self.route = "/"
        self.views = [Mock()]  # simulate the default home view

    def update(self):
        self.updated = True

    def show_dialog(self, control):
        self.opened_controls.append(control)


class MockControls:
    def __init__(self):
        self.warning_banner = MockText()
        self.path_preview_text = MockControl()
        self.status_icon = MockControl()
        self.status_text = MockText()
        self.copy_path_button = MockControl()
        self.project_path_input = MockControl(value="/test/path")
        self.project_name_input = MockControl(value="")
        self.python_version_dropdown = MockControl(value="3.14")
        self.create_git_checkbox = MockControl(value=False)
        self.include_starter_files_checkbox = MockControl(value=False)
        self.ui_project_checkbox = MockControl(value=False)
        self.other_projects_checkbox = MockControl(value=False)
        self.save_as_preset_button = MockControl()
        self.app_subfolders_label = MockText()
        self.subfolders_container = MockContainer()
        self.packages_label = MockText()
        self.packages_panel = Mock()
        self.add_package_button = MockControl()
        self.remove_package_button = MockControl()
        self.clear_packages_button = MockControl()
        self.progress_ring = MockControl()
        self.progress_bar = MockControl()
        self.progress_step_text = MockControl()
        self.build_project_button = MockControl()
        self.reset_button = MockControl()
        self.exit_button = MockControl()
        self.theme_toggle_button = Mock(icon=None)
        self.about_menu_item = MockControl()
        self.help_menu_item = MockControl()
        self.app_cheat_sheet_menu_item = MockControl()
        self.settings_menu_item = MockControl()
        self.history_menu_item = MockControl()
        self.log_viewer_menu_item = MockControl()
        self.overflow_menu = MockControl()
        self.check_pypi_button = MockControl()
        self.pypi_status_text = MockText()
        self.metadata_button = MockControl()
        self.metadata_checkbox = MockControl(value=False)
        self.metadata_summary = MockText()
        self.preset_dropdown = MockControl(value="None")
        self.edit_file_button = MockControl()
        self.edit_file_button.disabled = True
        self.section_titles = []
        self.section_containers = []


@pytest.fixture
def handlers():
    page = MockPage()
    controls = MockControls()
    state = AppState()
    h = Handlers(page, controls, state)
    return h, page, controls, state


# ---- get_canonical_file_path tests ----


class TestGetCanonicalFilePath:
    """Tests for the get_canonical_file_path helper."""

    def test_simple_file(self):
        folders = [{"name": "core", "subfolders": [], "files": ["state.py"]}]
        result = get_canonical_file_path(folders, [0, "files", 0])
        assert result == "core/state.py"

    def test_nested_file(self):
        folders = [
            {
                "name": "core",
                "subfolders": [
                    {"name": "utils", "subfolders": [], "files": ["helpers.py"]}
                ],
                "files": [],
            }
        ]
        result = get_canonical_file_path(folders, [0, "subfolders", 0, "files", 0])
        assert result == "core/utils/helpers.py"

    def test_second_folder(self):
        folders = [
            {"name": "core", "subfolders": [], "files": ["a.py"]},
            {"name": "ui", "subfolders": [], "files": ["b.py"]},
        ]
        result = get_canonical_file_path(folders, [1, "files", 0])
        assert result == "ui/b.py"

    def test_folder_path_only(self):
        folders = [{"name": "core", "subfolders": [], "files": []}]
        result = get_canonical_file_path(folders, [0])
        assert result == "core"

    def test_invalid_index(self):
        folders = [{"name": "core", "subfolders": [], "files": []}]
        result = get_canonical_file_path(folders, [5, "files", 0])
        assert result is None

    def test_empty_path(self):
        folders = [{"name": "core", "subfolders": [], "files": []}]
        result = get_canonical_file_path(folders, [])
        assert result is None

    def test_multiple_files(self):
        folders = [
            {"name": "core", "subfolders": [], "files": ["a.py", "b.py", "c.py"]}
        ]
        assert get_canonical_file_path(folders, [0, "files", 0]) == "core/a.py"
        assert get_canonical_file_path(folders, [0, "files", 1]) == "core/b.py"
        assert get_canonical_file_path(folders, [0, "files", 2]) == "core/c.py"

    def test_root_files_path(self):
        folders = []
        root_files = ["README.md", "LICENSE", "CHANGELOG.md"]
        result = get_canonical_file_path(
            folders, ["root_files", 0], root_files=root_files
        )
        assert result == "README.md"

    def test_root_files_path_second_item(self):
        root_files = ["README.md", "LICENSE", "CHANGELOG.md"]
        result = get_canonical_file_path([], ["root_files", 2], root_files=root_files)
        assert result == "CHANGELOG.md"

    def test_root_files_path_out_of_range(self):
        root_files = ["README.md"]
        result = get_canonical_file_path([], ["root_files", 5], root_files=root_files)
        assert result is None

    def test_root_files_path_without_root_files_param(self):
        result = get_canonical_file_path([], ["root_files", 0])
        assert result is None

    def test_root_files_path_with_empty_list(self):
        result = get_canonical_file_path([], ["root_files", 0], root_files=[])
        assert result is None


# ---- file_overrides in state tests ----


class TestFileOverridesState:
    """Tests for file_overrides field on AppState."""

    def test_default_empty(self):
        state = AppState()
        assert state.file_overrides == {}

    def test_reset_clears_overrides(self):
        state = AppState()
        state.file_overrides = {"core/main.py": "# custom"}
        state.reset()
        assert state.file_overrides == {}


# ---- file_overrides in filesystem_handler tests ----


class TestFileOverridesInBuild:
    """Tests that file_overrides take priority over boilerplate during build."""

    def test_override_wins_over_boilerplate(self):
        from uv_forger.handlers.filesystem_handler import create_folders

        with tempfile.TemporaryDirectory() as tmpdir:
            folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]
            overrides = {"core/main.py": "# custom content here"}
            create_folders(
                Path(tmpdir),
                folders,
                file_overrides=overrides,
            )
            content = (Path(tmpdir) / "core" / "main.py").read_text()
            assert content == "# custom content here"

    def test_no_override_falls_through(self):
        from uv_forger.handlers.filesystem_handler import create_folders

        with tempfile.TemporaryDirectory() as tmpdir:
            folders = [{"name": "core", "subfolders": [], "files": ["state.py"]}]
            # No overrides — file should still be created (empty touch)
            create_folders(Path(tmpdir), folders, file_overrides={})
            assert (Path(tmpdir) / "core" / "state.py").exists()
            assert (Path(tmpdir) / "core" / "state.py").read_text() == ""

    def test_nested_override(self):
        from uv_forger.handlers.filesystem_handler import create_folders

        with tempfile.TemporaryDirectory() as tmpdir:
            folders = [
                {
                    "name": "core",
                    "subfolders": [
                        {"name": "utils", "subfolders": [], "files": ["helpers.py"]}
                    ],
                    "files": [],
                }
            ]
            overrides = {"core/utils/helpers.py": "def helper(): pass"}
            create_folders(Path(tmpdir), folders, file_overrides=overrides)
            content = (Path(tmpdir) / "core" / "utils" / "helpers.py").read_text()
            assert content == "def helper(): pass"


# ---- Context menu + pencil icon tests ----


class TestContextMenuAndIndicator:
    """Tests for context menu on files and pencil icon indicator."""

    def test_file_item_returns_context_menu(self, handlers):
        h, _, _, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]

        result = h._create_item_container("main.py", [0, "files", 0], "file")
        # Should be a ContextMenu (has secondary_items)
        assert hasattr(result, "secondary_items")
        assert len(result.secondary_items) == 4

    def test_folder_item_returns_context_menu(self, handlers):
        h, _, _, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": []}]

        result = h._create_item_container("core", [0], "folder")
        # Should be a ContextMenu wrapping the folder container
        assert hasattr(result, "secondary_items")
        assert result.content.data["type"] == "folder"

    def test_pencil_icon_when_override_exists(self, handlers):
        h, _, _, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]
        state.file_overrides = {"core/main.py": "# custom"}

        result = h._create_item_container("main.py", [0, "files", 0], "file")
        inner = result.content  # ContextMenu -> Container
        row_controls = inner.content.controls
        # Should have 3 items: file icon, text, pencil icon
        assert len(row_controls) == 3

    def test_no_pencil_icon_without_override(self, handlers):
        h, _, _, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]
        state.file_overrides = {}

        result = h._create_item_container("main.py", [0, "files", 0], "file")
        inner = result.content
        row_controls = inner.content.controls
        # Should have 2 items: file icon, text (no pencil)
        assert len(row_controls) == 2

    def test_edit_file_button_disabled_for_folder_selection(self, handlers):
        h, _, controls, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": []}]

        event = Mock()
        event.control = Mock()
        event.control.data = {"path": [0], "type": "folder", "name": "core"}
        h._on_item_click(event)
        assert controls.edit_file_button.disabled is True

    def test_edit_file_button_enabled_for_file_selection(self, handlers):
        h, _, controls, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]

        event = Mock()
        event.control = Mock()
        event.control.data = {
            "path": [0, "files", 0],
            "type": "file",
            "name": "main.py",
        }
        h._on_item_click(event)
        assert controls.edit_file_button.disabled is False


class TestResetFileOverride:
    """Tests for the _reset_file_override method."""

    def test_reset_removes_override(self, handlers):
        h, _, _, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]
        state.file_overrides = {"core/main.py": "# custom"}

        h._reset_file_override([0, "files", 0], "main.py")
        assert "core/main.py" not in state.file_overrides

    def test_reset_no_op_without_override(self, handlers):
        h, _, _, state = handlers
        state.folders = [{"name": "core", "subfolders": [], "files": ["main.py"]}]
        state.file_overrides = {}

        # Should not raise
        h._reset_file_override([0, "files", 0], "main.py")
        assert state.file_overrides == {}


# ---- create_file_editor_view tests ----


class TestCreateFileEditorView:
    """Tests for the create_file_editor_view function."""

    def test_returns_ft_view(self):
        from uv_forger.ui.dialogs import create_file_editor_view

        view = create_file_editor_view(
            filename="main.py",
            initial_content="# hello",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=True,
        )
        assert isinstance(view, ft.View)
        assert view.route == "/editor"

    def test_view_exposes_editor_handle(self):
        from fce_enhanced import EditorHandle

        from uv_forger.ui.dialogs import create_file_editor_view

        view = create_file_editor_view(
            filename="main.py",
            initial_content="# hello",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=True,
        )
        assert isinstance(view.editor_handle, EditorHandle)

    def test_bare_filename_without_user_template_path(self):
        from uv_forger.ui.dialogs import create_file_editor_view

        view = create_file_editor_view(
            filename="main.py",
            initial_content="# hello",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=True,
        )
        assert view.editor_save_path == "main.py"

    def test_user_template_path_is_the_save_target(self):
        from uv_forger.ui.dialogs import create_file_editor_view

        user_path = str(
            Path.home()
            / "Library/Application Support/UV Forger/boilerplate/flet/main.py"
        )
        view = create_file_editor_view(
            filename="main.py",
            initial_content="# hello",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=True,
            user_template_path=user_path,
        )
        assert view.editor_save_path == user_path

    def test_user_template_path_none_falls_back_to_filename(self):
        from uv_forger.ui.dialogs import create_file_editor_view

        view = create_file_editor_view(
            filename="state.py",
            initial_content="",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=False,
            user_template_path=None,
        )
        assert view.editor_save_path == "state.py"

    def test_editor_has_keyboard_shortcuts_disabled(self):
        """Editor should have register_keyboard_shortcuts=False so the app handles them."""
        from uv_forger.ui.dialogs import create_file_editor_view

        view = create_file_editor_view(
            filename="main.py",
            initial_content="# hello",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=True,
        )
        # Component kwargs are frozen at render time
        editor = view.controls[1].content.controls[0]
        assert editor.kwargs["register_keyboard_shortcuts"] is False
        assert editor.kwargs["expand"] is True

    def test_editor_component_is_memoized(self):
        """Without memo, any imperative page.update() re-renders the editor into
        controls with new ids the client was never told about, and every click
        inside the editor is silently dropped."""
        from uv_forger.ui.dialogs import create_file_editor_view

        view = create_file_editor_view(
            filename="main.py",
            initial_content="# hello",
            on_save=lambda c: None,
            on_reset=lambda: None,
            on_close=lambda: None,
            is_dark_mode=True,
        )
        editor = view.controls[1].content.controls[0]
        assert editor.memoized is True
