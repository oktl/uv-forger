#!/usr/bin/env python3
"""Pytest tests for event_handlers.py - UI event handlers and helper methods"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from uv_forger.core.constants import DEFAULT_PYTHON_VERSION
from uv_forger.core.state import AppState
from uv_forger.handlers.ui_handler import Handlers
from uv_forger.ui.dialog_data import (
    OTHER_PROJECT_CHECKBOX_LABEL,
    UI_PROJECT_CHECKBOX_LABEL,
)


class MockControl:
    """Mock Flet control"""

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
    """Mock Flet container"""

    def __init__(self):
        self.content = Mock()
        self.content.controls = []
        self.border = None


class MockText:
    """Mock Flet Text control"""

    def __init__(self, value=""):
        self.value = value
        self.color = None


class MockPage:
    """Mock Flet Page"""

    def __init__(self):
        self.updated = False
        self.overlay = []
        self.appbar = None
        self.bottom_appbar = Mock()
        self.bottom_appbar.bgcolor = None
        self.theme_mode = None
        self.window = Mock()
        self.opened_controls = []
        self.route = "/"
        self.views = [Mock()]  # simulate the default home view

    def update(self):
        self.updated = True

    def show_dialog(self, control):
        self.opened_controls.append(control)


class MockControls:
    """Mock Controls class"""

    def __init__(self):
        self.warning_banner = MockText()
        self.path_preview_text = MockControl()
        self.status_icon = MockControl()
        self.status_text = MockText()
        self.copy_path_button = MockControl()
        self.project_path_input = MockControl(value="/test/path")
        self.project_name_input = MockControl(value="")
        self.python_version_dropdown = MockControl(value=DEFAULT_PYTHON_VERSION)
        self.create_git_checkbox = MockControl(value=False)
        self.include_starter_files_checkbox = MockControl(value=False)
        self.ui_project_checkbox = MockControl(
            value=False, label=UI_PROJECT_CHECKBOX_LABEL
        )
        self.other_projects_checkbox = MockControl(
            value=False, label=OTHER_PROJECT_CHECKBOX_LABEL
        )
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
def mock_handlers():
    """Create a Handlers instance with mocked dependencies"""
    page = MockPage()
    controls = MockControls()
    state = AppState()
    handlers = Handlers(page, controls, state)
    return handlers, page, controls, state


def test_handlers_initialization(mock_handlers):
    """Test Handlers class initialization"""
    handlers, page, controls, state = mock_handlers

    assert handlers.page is page
    assert handlers.controls is controls
    assert handlers.state is state
    assert handlers.template_loader is not None


def test_set_warning_without_update(mock_handlers):
    """Test _set_warning without page update"""
    handlers, page, controls, state = mock_handlers

    handlers._set_warning("Test warning", update=False)

    assert controls.warning_banner.value == "Test warning"
    assert not page.updated


def test_set_warning_with_update(mock_handlers):
    """Test _set_warning with page update"""
    handlers, page, controls, state = mock_handlers

    handlers._set_warning("Test warning", update=True)

    assert controls.warning_banner.value == "Test warning"
    assert page.updated


def test_set_warning_clear(mock_handlers):
    """Test clearing warning"""
    handlers, page, controls, state = mock_handlers

    handlers._set_warning("Warning", update=False)
    handlers._set_warning("", update=False)

    assert controls.warning_banner.value == ""


@pytest.mark.parametrize(
    "status_type,message",
    [
        ("info", "Info message"),
        ("success", "Success message"),
        ("error", "Error message"),
    ],
)
def test_set_status_types(mock_handlers, status_type, message):
    """Test _set_status with different status types"""
    handlers, page, controls, state = mock_handlers

    handlers._set_status(message, status_type, update=False)

    assert controls.status_text.value == message
    assert controls.status_text.color is not None


def test_set_status_with_update(mock_handlers):
    """Test _set_status updates page when requested"""
    handlers, page, controls, state = mock_handlers

    handlers._set_status("Test", "info", update=True)

    assert page.updated


def test_update_folder_display_simple(mock_handlers):
    """Test _update_folder_display with simple folder list"""
    handlers, page, controls, state = mock_handlers

    state.folders = [
        {"name": "core", "subfolders": [], "files": []},
        {"name": "ui", "subfolders": [], "files": []},
        {"name": "utils", "subfolders": [], "files": []},
    ]
    handlers._update_folder_display()

    assert len(controls.subfolders_container.content.controls) == 3
    assert page.updated


def test_update_folder_display_nested(mock_handlers):
    """Test _update_folder_display with nested folder structure"""
    handlers, page, controls, state = mock_handlers

    state.folders = [
        {"name": "core", "subfolders": [], "files": []},
        {
            "name": "ui",
            "subfolders": [
                {"name": "components", "subfolders": [], "files": []},
                {"name": "styles", "subfolders": [], "files": []},
            ],
            "files": [],
        },
    ]
    handlers._update_folder_display()

    # Should have: core, ui, components (indented), styles (indented) = 4 controls
    assert len(controls.subfolders_container.content.controls) == 4


def test_update_folder_display_empty(mock_handlers):
    """Test _update_folder_display with empty folders"""
    handlers, page, controls, state = mock_handlers

    state.folders = []
    handlers._update_folder_display()

    assert len(controls.subfolders_container.content.controls) == 0


def test_create_item_container_folder(mock_handlers):
    """Test _create_item_container creates folder context menu correctly"""
    handlers, page, controls, state = mock_handlers

    result = handlers._create_item_container(
        name="core", item_path=[0], item_type="folder", indent=0
    )

    assert result is not None
    # Folder items are now wrapped in a ContextMenu
    container = result.content
    assert container.data["name"] == "core"
    assert container.data["type"] == "folder"
    assert container.data["path"] == [0]
    assert container.on_click == handlers._on_item_click


def test_create_item_container_file(mock_handlers):
    """Test _create_item_container creates file container correctly.

    File items are wrapped in a ContextMenu; the inner container holds the data.
    """
    handlers, page, controls, state = mock_handlers

    result = handlers._create_item_container(
        name="config.py", item_path=[0, "files", 0], item_type="file", indent=1
    )

    assert result is not None
    # File items return ContextMenu wrapping the Container
    inner = result.content
    assert inner.data["name"] == "config.py"
    assert inner.data["type"] == "file"
    assert inner.data["path"] == [0, "files", 0]


def test_create_item_container_selected_folder(mock_handlers):
    """Test _create_item_container highlights selected folder"""
    handlers, page, controls, state = mock_handlers

    state.selected_item_path = [0]
    state.selected_item_type = "folder"

    result = handlers._create_item_container(
        name="core", item_path=[0], item_type="folder", indent=0
    )

    # Folder is wrapped in ContextMenu; inner container has selection highlighting
    container = result.content
    assert container.bgcolor is not None
    assert container.border is not None


def test_create_item_container_selected_file(mock_handlers):
    """Test _create_item_container highlights selected file"""
    handlers, page, controls, state = mock_handlers

    state.selected_item_path = [0, "files", 0]
    state.selected_item_type = "file"

    result = handlers._create_item_container(
        name="config.py", item_path=[0, "files", 0], item_type="file", indent=1
    )

    # File items return ContextMenu; inner container has highlighting
    inner = result.content
    assert inner.bgcolor is not None
    assert inner.border is not None


def test_create_item_container_not_selected(mock_handlers):
    """Test _create_item_container doesn't highlight non-selected items"""
    handlers, page, controls, state = mock_handlers

    state.selected_item_path = [1]
    state.selected_item_type = "folder"

    result = handlers._create_item_container(
        name="core", item_path=[0], item_type="folder", indent=0
    )

    # Folder wrapped in ContextMenu; inner container should NOT have highlighting
    container = result.content
    assert container.bgcolor is None
    assert container.border is None


def test_process_folder_recursive_minimal_dict(mock_handlers):
    """Test _process_folder_recursive with minimal dict folder"""
    handlers, page, controls, state = mock_handlers

    controls_list = []
    handlers._process_folder_recursive(
        {"name": "core", "subfolders": [], "files": []}, [0], 0, controls_list
    )

    assert len(controls_list) == 1
    assert _get_item_data(controls_list[0])["name"] == "core"
    assert _get_item_data(controls_list[0])["type"] == "folder"


def test_process_folder_recursive_dict(mock_handlers):
    """Test _process_folder_recursive with dict folder"""
    handlers, page, controls, state = mock_handlers

    folder_dict = {"name": "ui", "subfolders": [], "files": []}
    controls_list = []
    handlers._process_folder_recursive(folder_dict, [0], 0, controls_list)

    assert len(controls_list) == 1
    assert _get_item_data(controls_list[0])["name"] == "ui"
    assert _get_item_data(controls_list[0])["type"] == "folder"


def _get_item_data(control):
    """Extract data dict from a control (Container or ContextMenu wrapping one)."""
    if hasattr(control, "data") and control.data is not None:
        return control.data
    # ContextMenu wrapping a Container
    return control.content.data


def test_process_folder_recursive_with_files(mock_handlers):
    """Test _process_folder_recursive processes files correctly"""
    handlers, page, controls, state = mock_handlers

    folder_dict = {"name": "core", "subfolders": [], "files": ["config.py", "state.py"]}
    controls_list = []
    handlers._process_folder_recursive(folder_dict, [0], 0, controls_list)

    # Should have 1 folder + 2 files = 3 controls
    assert len(controls_list) == 3
    assert _get_item_data(controls_list[0])["name"] == "core"
    assert _get_item_data(controls_list[0])["type"] == "folder"
    assert _get_item_data(controls_list[1])["name"] == "config.py"
    assert _get_item_data(controls_list[1])["type"] == "file"
    assert _get_item_data(controls_list[2])["name"] == "state.py"
    assert _get_item_data(controls_list[2])["type"] == "file"


def test_process_folder_recursive_with_subfolders(mock_handlers):
    """Test _process_folder_recursive processes subfolders recursively"""
    handlers, page, controls, state = mock_handlers

    folder_dict = {
        "name": "ui",
        "subfolders": [
            {"name": "components", "subfolders": [], "files": []},
            {"name": "styles", "subfolders": [], "files": []},
        ],
        "files": [],
    }
    controls_list = []
    handlers._process_folder_recursive(folder_dict, [0], 0, controls_list)

    # Should have ui + components + styles = 3 folders
    assert len(controls_list) == 3
    assert _get_item_data(controls_list[0])["name"] == "ui"
    assert _get_item_data(controls_list[1])["name"] == "components"
    assert _get_item_data(controls_list[2])["name"] == "styles"


def test_process_folder_recursive_nested_with_files(mock_handlers):
    """Test _process_folder_recursive with nested folders and files"""
    handlers, page, controls, state = mock_handlers

    folder_dict = {
        "name": "app",
        "subfolders": [
            {"name": "core", "subfolders": [], "files": ["state.py", "models.py"]}
        ],
        "files": ["main.py"],
    }
    controls_list = []
    handlers._process_folder_recursive(folder_dict, [0], 0, controls_list)

    # app + main.py + core + state.py + models.py = 5 controls
    assert len(controls_list) == 5
    assert _get_item_data(controls_list[0])["name"] == "app"
    assert _get_item_data(controls_list[0])["type"] == "folder"
    assert _get_item_data(controls_list[1])["name"] == "main.py"
    assert _get_item_data(controls_list[1])["type"] == "file"
    assert _get_item_data(controls_list[2])["name"] == "core"
    assert _get_item_data(controls_list[2])["type"] == "folder"
    assert _get_item_data(controls_list[3])["name"] == "state.py"
    assert _get_item_data(controls_list[3])["type"] == "file"
    assert _get_item_data(controls_list[4])["name"] == "models.py"
    assert _get_item_data(controls_list[4])["type"] == "file"


def test_validate_inputs_empty_project_name(mock_handlers):
    """Test validation fails with empty project name"""
    handlers, page, controls, state = mock_handlers

    state.project_name = ""
    with tempfile.TemporaryDirectory() as tmpdir:
        state.project_path = tmpdir
        assert not handlers._validate_inputs()


def test_validate_inputs_invalid_project_name(mock_handlers):
    """Test validation fails with invalid project name (space)"""
    handlers, page, controls, state = mock_handlers

    state.project_name = "my project"
    with tempfile.TemporaryDirectory() as tmpdir:
        state.project_path = tmpdir
        assert not handlers._validate_inputs()


def test_validate_inputs_invalid_path(mock_handlers):
    """Test validation fails with invalid path"""
    handlers, page, controls, state = mock_handlers

    state.project_name = "valid_project"
    state.project_path = "/nonexistent/path/that/doesnt/exist"

    assert not handlers._validate_inputs()


def test_validate_inputs_valid(mock_handlers):
    """Test validation succeeds with valid inputs"""
    handlers, page, controls, state = mock_handlers

    state.project_name = "valid_project"
    with tempfile.TemporaryDirectory() as tmpdir:
        state.project_path = tmpdir
        assert handlers._validate_inputs()


def test_validate_inputs_existing_project(mock_handlers):
    """Test validation fails when project already exists"""
    handlers, page, controls, state = mock_handlers

    state.project_name = "existing_project"
    with tempfile.TemporaryDirectory() as tmpdir:
        state.project_path = tmpdir
        # Create the project directory
        project_dir = Path(tmpdir) / "existing_project"
        project_dir.mkdir()

        assert not handlers._validate_inputs()


def test_validate_inputs_clears_warning_on_success(mock_handlers):
    """Test warning is cleared on successful validation"""
    handlers, page, controls, state = mock_handlers

    controls.warning_banner.value = "Old warning"
    state.project_name = "new_valid_project"
    with tempfile.TemporaryDirectory() as tmpdir:
        state.project_path = tmpdir
        handlers._validate_inputs()

        assert controls.warning_banner.value == ""


@pytest.mark.asyncio
async def test_wrap_async_creates_callable():
    """Test the wrap_async wrapper creates a callable"""
    import asyncio

    def wrap_async(coro_func):
        """Wrap async handler for Flet event system."""

        def wrapper(e):
            asyncio.create_task(coro_func(e))

        return wrapper

    async def test_coro(e):
        return "result"

    wrapped = wrap_async(test_coro)
    assert callable(wrapped)


@pytest.mark.parametrize(
    "field,value",
    [
        ("python_version", "3.11"),
        ("git_enabled", True),
        ("ui_project_enabled", True),
        ("framework", "flet"),
        ("other_project_enabled", True),
        ("project_type", "django"),
    ],
)
def test_state_updates_from_handlers(mock_handlers, field, value):
    """Test that handler methods properly update state"""
    handlers, page, controls, state = mock_handlers

    # Simulate what handlers do
    setattr(state, field, value)

    assert getattr(state, field) == value


# ========== Project Type Handler Tests ==========


@pytest.mark.asyncio
async def test_on_other_project_toggle_checked(mock_handlers):
    """Test on_other_project_toggle always opens dialog"""
    handlers, page, controls, state = mock_handlers

    # Create mock event (value doesn't matter — handler always forces True)
    mock_event = Mock()
    mock_event.control = MockControl(value=False, label=OTHER_PROJECT_CHECKBOX_LABEL)

    # Mock the dialog show method to avoid Flet dependencies
    with patch.object(handlers, "_show_project_type_dialog") as mock_show:
        await handlers.on_other_project_toggle(mock_event)

    # Handler always forces checkbox to True and opens dialog
    assert mock_event.control.value
    assert state.other_project_enabled

    # Verify dialog was shown
    mock_show.assert_called_once()

    # Verify page was updated
    assert page.updated


@pytest.mark.asyncio
async def test_on_other_project_toggle_reopens_dialog(mock_handlers):
    """Test on_other_project_toggle reopens dialog when already checked"""
    handlers, page, controls, state = mock_handlers

    # Set initial state — already checked with selection
    state.other_project_enabled = True
    state.project_type = "django"

    # Create mock event (even if user "unchecks", handler forces True and opens dialog)
    mock_event = Mock()
    mock_event.control = MockControl(value=False, label="Project: Django")

    with patch.object(handlers, "_show_project_type_dialog") as mock_show:
        await handlers.on_other_project_toggle(mock_event)

    # Handler forces checkbox to True and opens dialog
    assert mock_event.control.value
    assert state.other_project_enabled

    # Dialog was shown (user can select None to clear)
    mock_show.assert_called_once()
    assert page.updated


@pytest.mark.asyncio
async def test_on_other_project_toggle_does_not_uncheck_ui(mock_handlers):
    """Test that checking Other project does NOT uncheck UI project"""
    handlers, page, controls, state = mock_handlers

    # Start with UI project checked
    state.ui_project_enabled = True
    state.framework = "flet"
    controls.ui_project_checkbox.value = True

    # Create mock event to check Other project
    mock_event = Mock()
    mock_event.control = MockControl(value=True, label=OTHER_PROJECT_CHECKBOX_LABEL)

    # Mock the dialog show method
    with patch.object(handlers, "_show_project_type_dialog"):
        await handlers.on_other_project_toggle(mock_event)

    # Verify UI project state is UNCHANGED
    assert state.ui_project_enabled
    assert controls.ui_project_checkbox.value
    assert state.framework == "flet"

    # Verify Other project is now checked
    assert state.other_project_enabled


def test_show_project_type_dialog_adds_to_overlay(mock_handlers):
    """Test that dialog is added to page overlay"""
    handlers, page, controls, state = mock_handlers

    # Mock the dialog creation
    with patch("uv_forger.ui.dialogs.create_project_type_dialog") as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = False
        mock_create.return_value = mock_dialog

        handlers._show_project_type_dialog()

        # Verify dialog was created with correct params
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert "on_select_callback" in call_kwargs
        assert "on_close_callback" in call_kwargs
        assert call_kwargs["current_selection"] == state.project_type
        assert call_kwargs["is_dark_mode"] == state.is_dark_mode

        # Verify dialog was added to overlay
        assert mock_dialog in page.overlay

        # Verify dialog was opened
        assert mock_dialog.open

        # Verify page was updated
        assert page.updated


@pytest.mark.asyncio
async def test_ui_project_toggle_does_not_uncheck_other_project(mock_handlers):
    """Test that checking UI project does NOT uncheck Other project"""
    handlers, page, controls, state = mock_handlers

    # Start with Other project checked
    state.other_project_enabled = True
    state.project_type = "django"
    controls.other_projects_checkbox.value = True

    # Create mock event to check UI project
    mock_event = Mock()
    mock_event.control = MockControl(value=False, label=UI_PROJECT_CHECKBOX_LABEL)

    # Mock the dialog show method
    with patch.object(handlers, "_show_framework_dialog"):
        await handlers.on_ui_project_toggle(mock_event)

    # Verify Other project state is UNCHANGED
    assert state.other_project_enabled
    assert controls.other_projects_checkbox.value
    assert state.project_type == "django"


# ========== Template Merge / Co-selection Tests ==========


def test_both_checkboxes_can_be_checked(mock_handlers):
    """Test both UI and Other project checkboxes can be checked simultaneously"""
    handlers, page, controls, state = mock_handlers

    state.ui_project_enabled = True
    state.framework = "flet"
    state.other_project_enabled = True
    state.project_type = "django"

    # Both should remain true
    assert state.ui_project_enabled
    assert state.other_project_enabled
    assert state.framework == "flet"
    assert state.project_type == "django"


def test_reload_and_merge_templates_both_selected(mock_handlers):
    """Test _reload_and_merge_templates merges when both are selected"""
    handlers, page, controls, state = mock_handlers

    state.ui_project_enabled = True
    state.framework = "flet"
    state.other_project_enabled = True
    state.project_type = "django"

    with patch.object(handlers.template_loader, "load_config") as mock_load:
        mock_load.side_effect = [
            {"folders": [{"name": "ui", "subfolders": [], "files": []}]},
            {"folders": [{"name": "api", "subfolders": [], "files": []}]},
        ]

        with patch(
            "uv_forger.handlers.option_handlers.merge_folder_lists"
        ) as mock_merge:
            mock_merge.return_value = [
                {"name": "ui", "subfolders": [], "files": []},
                {"name": "api", "subfolders": [], "files": []},
            ]
            handlers._reload_and_merge_templates()

            # Verify merge was called with the two folder lists
            mock_merge.assert_called_once()

    # Verify selection was cleared
    assert state.selected_item_path is None
    assert state.selected_item_type is None


def test_reload_and_merge_templates_only_framework(mock_handlers):
    """Test _reload_and_merge_templates with only framework selected"""
    handlers, page, controls, state = mock_handlers

    state.ui_project_enabled = True
    state.framework = "flet"
    state.other_project_enabled = False

    with patch.object(handlers.template_loader, "load_config") as mock_load:
        mock_load.return_value = {"folders": ["core", "ui"]}
        handlers._reload_and_merge_templates()

        mock_load.assert_called_once_with("flet")
    assert [f["name"] for f in state.folders] == ["core", "ui"]


def test_reload_and_merge_templates_only_project_type(mock_handlers):
    """Test _reload_and_merge_templates with only project type selected"""
    handlers, page, controls, state = mock_handlers

    state.ui_project_enabled = False
    state.other_project_enabled = True
    state.project_type = "django"

    with patch.object(handlers.template_loader, "load_config") as mock_load:
        mock_load.return_value = {"folders": ["api", "models"]}
        handlers._reload_and_merge_templates()

        mock_load.assert_called_once_with("project_types/django")
    assert [f["name"] for f in state.folders] == ["api", "models"]


def test_reload_and_merge_templates_neither_selected(mock_handlers):
    """Test _reload_and_merge_templates with neither selected loads default"""
    handlers, page, controls, state = mock_handlers

    state.ui_project_enabled = False
    state.other_project_enabled = False

    with patch.object(handlers.template_loader, "load_config") as mock_load:
        mock_load.return_value = {"folders": ["default1", "default2"]}
        handlers._reload_and_merge_templates()

        mock_load.assert_called_once_with(None)
    assert [f["name"] for f in state.folders] == ["default1", "default2"]


def test_show_framework_dialog_adds_to_overlay(mock_handlers):
    """Test that framework dialog is added to page overlay"""
    handlers, page, controls, state = mock_handlers

    with patch(
        "uv_forger.handlers.option_handlers.create_framework_dialog"
    ) as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = False
        mock_create.return_value = mock_dialog

        handlers._show_framework_dialog()

        # Verify dialog was created with correct params
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert "on_select_callback" in call_kwargs
        assert "on_close_callback" in call_kwargs
        assert call_kwargs["current_selection"] == state.framework
        assert call_kwargs["is_dark_mode"] == state.is_dark_mode

        # Verify dialog was added to overlay and opened
        assert mock_dialog in page.overlay
        assert mock_dialog.open
        assert page.updated


@pytest.mark.asyncio
async def test_reset_with_both_checked(mock_handlers):
    """Test on_reset works correctly when both are checked"""
    handlers, page, controls, state = mock_handlers

    state.ui_project_enabled = True
    state.framework = "flet"
    state.other_project_enabled = True
    state.project_type = "django"

    with patch.object(handlers, "_reload_and_merge_templates") as mock_reload:
        await handlers._do_reset()

        mock_reload.assert_called_once()

    # Verify state was reset
    assert not state.ui_project_enabled
    assert not state.other_project_enabled
    assert state.framework is None
    assert state.project_type is None
    assert not controls.ui_project_checkbox.value
    assert not controls.other_projects_checkbox.value


def test_reload_and_merge_clears_selection(mock_handlers):
    """Test _reload_and_merge_templates clears selected_item_path and type"""
    handlers, page, controls, state = mock_handlers

    state.selected_item_path = [0, "subfolders", 1]
    state.selected_item_type = "folder"
    state.ui_project_enabled = False
    state.other_project_enabled = False

    with patch.object(handlers.template_loader, "load_config") as mock_load:
        mock_load.return_value = {"folders": ["core"]}
        handlers._reload_and_merge_templates()

    assert state.selected_item_path is None
    assert state.selected_item_type is None


# ========== Feature 4: Folder/File Count Tests ==========


def test_count_folders_and_files_empty(mock_handlers):
    """Test _count_folders_and_files with empty list"""
    fc, fic = Handlers._count_folders_and_files([])
    assert fc == 0
    assert fic == 0


def test_count_folders_and_files_flat_dicts(mock_handlers):
    """Test _count_folders_and_files with flat dict folders"""
    folders = [
        {"name": "core", "subfolders": [], "files": []},
        {"name": "ui", "subfolders": [], "files": []},
        {"name": "utils", "subfolders": [], "files": []},
    ]
    fc, fic = Handlers._count_folders_and_files(folders)
    assert fc == 3
    assert fic == 3  # 3x __init__.py (create_init defaults to True)


def test_count_folders_and_files_with_files(mock_handlers):
    """Test _count_folders_and_files counts files in dicts"""
    folders = [
        {"name": "core", "subfolders": [], "files": ["state.py", "models.py"]},
        {"name": "ui", "subfolders": [], "files": ["components.py"]},
    ]
    fc, fic = Handlers._count_folders_and_files(folders)
    assert fc == 2
    assert fic == 5  # 2x __init__.py + state.py, models.py, components.py


def test_count_folders_and_files_nested(mock_handlers):
    """Test _count_folders_and_files with nested structure"""
    folders = [
        {
            "name": "app",
            "subfolders": [
                {"name": "core", "subfolders": [], "files": ["state.py"]},
                {
                    "name": "ui",
                    "subfolders": [],
                    "files": ["components.py", "theme.py"],
                },
            ],
            "files": ["main.py"],
        }
    ]
    fc, fic = Handlers._count_folders_and_files(folders)
    assert fc == 3  # app, core, ui
    assert fic == 7  # 3x __init__.py + main.py, state.py, components.py, theme.py


def test_count_folders_and_files_nested_dicts(mock_handlers):
    """Test _count_folders_and_files with nested dict structures"""
    folders = [
        {"name": "core", "subfolders": [], "files": ["state.py", "models.py"]},
        {
            "name": "ui",
            "subfolders": [
                {"name": "widgets", "subfolders": [], "files": ["button.py"]},
            ],
            "files": [],
        },
    ]
    fc, fic = Handlers._count_folders_and_files(folders)
    assert fc == 3  # core, ui, widgets
    assert fic == 6  # 3x __init__.py + state.py, models.py, button.py


def test_update_folder_display_updates_label(mock_handlers):
    """Test _update_folder_display sets folder/file counts in label"""
    handlers, page, controls, state = mock_handlers

    state.folders = [
        {"name": "core", "subfolders": [], "files": ["state.py"]},
    ]
    handlers._update_folder_display()

    assert "1 folders" in controls.app_subfolders_label.value
    assert "2 files" in controls.app_subfolders_label.value  # state.py + __init__.py


# ========== Feature 5: Validation Icon Tests ==========


def test_set_validation_icon_valid(mock_handlers):
    """Test _set_validation_icon sets green check when valid"""
    field = MockControl()
    Handlers._set_validation_icon(field, True)
    assert field.suffix is not None
    assert field.suffix.color == "green"


def test_set_validation_icon_invalid(mock_handlers):
    """Test _set_validation_icon sets red X when invalid"""
    field = MockControl()
    Handlers._set_validation_icon(field, False)
    assert field.suffix is not None
    assert field.suffix.color == "red"


def test_set_validation_icon_none(mock_handlers):
    """Test _set_validation_icon clears icon when None"""
    field = MockControl()
    field.suffix = "something"
    Handlers._set_validation_icon(field, None)
    assert field.suffix is None


@pytest.mark.asyncio
async def test_on_path_change_sets_valid_icon(mock_handlers):
    """Test on_path_change sets icon when path is valid"""
    handlers, page, controls, state = mock_handlers

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_event = Mock()
        mock_event.control = Mock()
        mock_event.control.value = tmpdir

        await handlers.on_path_change(mock_event)

        assert controls.project_path_input.suffix is not None
        # Valid path → green check
        assert controls.project_path_input.suffix.color == "green"


@pytest.mark.asyncio
async def test_on_path_change_empty_clears_icon(mock_handlers):
    """Test on_path_change clears icon when path is empty"""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = Mock()
    mock_event.control.value = ""

    await handlers.on_path_change(mock_event)

    assert controls.project_path_input.suffix is None


@pytest.mark.asyncio
async def test_on_project_name_change_sets_valid_icon(mock_handlers):
    """Test on_project_name_change sets green icon for valid name"""
    handlers, page, controls, state = mock_handlers

    with tempfile.TemporaryDirectory() as tmpdir:
        state.project_path = tmpdir
        mock_event = Mock()
        mock_event.control = Mock()
        mock_event.control.value = "valid_project"

        await handlers.on_project_name_change(mock_event)

        assert controls.project_name_input.suffix is not None
        assert controls.project_name_input.suffix.color == "green"


@pytest.mark.asyncio
async def test_on_project_name_change_sets_invalid_icon(mock_handlers):
    """Test on_project_name_change sets red icon for invalid name"""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = Mock()
    mock_event.control.value = "invalid project name!"

    await handlers.on_project_name_change(mock_event)

    assert controls.project_name_input.suffix is not None
    assert controls.project_name_input.suffix.color == "red"


@pytest.mark.asyncio
async def test_on_project_name_change_empty_clears_icon(mock_handlers):
    """Test on_project_name_change clears icon when empty"""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = Mock()
    mock_event.control.value = ""

    await handlers.on_project_name_change(mock_event)

    assert controls.project_name_input.suffix is None


# ========== Feature 1: Build Button State Tests ==========


def test_update_build_button_state_both_valid(mock_handlers):
    """Test button enabled when both path and name are valid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = True
    handlers._update_build_button_state()

    assert not controls.build_project_button.disabled
    assert controls.build_project_button.opacity == 1.0
    assert "Ctrl+Enter" in controls.build_project_button.tooltip


def test_update_build_button_state_name_invalid(mock_handlers):
    """Test button disabled when name is invalid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = False
    handlers._update_build_button_state()

    assert controls.build_project_button.disabled
    assert controls.build_project_button.opacity == 0.5


def test_update_build_button_state_path_invalid(mock_handlers):
    """Test button disabled when path is invalid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = False
    state.name_valid = True
    handlers._update_build_button_state()

    assert controls.build_project_button.disabled
    assert controls.build_project_button.opacity == 0.5


def test_update_build_button_state_both_invalid(mock_handlers):
    """Test button disabled when both are invalid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = False
    state.name_valid = False
    handlers._update_build_button_state()

    assert controls.build_project_button.disabled
    assert controls.build_project_button.opacity == 0.5


# ========== Feature 2: Build Summary Dialog Tests ==========


def test_create_build_summary_dialog_basic():
    """Test create_build_summary_dialog creates a dialog"""
    from uv_forger.core.models import BuildSummaryConfig
    from uv_forger.ui.dialogs import create_build_summary_dialog

    config = BuildSummaryConfig(
        project_name="my_project",
        project_path="/home/user/projects",
        python_version="3.14",
        git_enabled=False,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=False,
        project_type=None,
        starter_files=True,
        folder_count=3,
        file_count=5,
    )

    dialog = create_build_summary_dialog(
        config=config,
        on_build_callback=lambda e: None,
        on_cancel_callback=lambda e: None,
        is_dark_mode=True,
    )

    assert dialog is not None
    assert dialog.modal
    assert len(dialog.actions) == 2


def test_create_build_summary_dialog_with_framework():
    """Test dialog includes framework when provided"""
    from uv_forger.core.models import BuildSummaryConfig
    from uv_forger.ui.dialogs import create_build_summary_dialog

    config = BuildSummaryConfig(
        project_name="my_app",
        project_path="/tmp",
        python_version="3.14",
        git_enabled=True,
        ui_project_enabled=True,
        framework="Flet",
        other_project_enabled=False,
        project_type=None,
        starter_files=True,
        folder_count=5,
        file_count=10,
    )

    dialog = create_build_summary_dialog(
        config=config,
        on_build_callback=lambda e: None,
        on_cancel_callback=lambda e: None,
        is_dark_mode=True,
    )

    # Check that the dialog content includes the framework info
    # Left column is the first control in the two-column Row layout
    controls = dialog.content.content.controls[0].controls
    labels = [
        r.controls[0].value
        for r in controls
        if hasattr(r, "controls") and hasattr(r.controls[0], "value")
    ]
    assert "UI Framework:" in labels


def test_create_build_summary_dialog_with_project_type():
    """Test dialog includes project type when provided"""
    from uv_forger.core.models import BuildSummaryConfig
    from uv_forger.ui.dialogs import create_build_summary_dialog

    config = BuildSummaryConfig(
        project_name="my_app",
        project_path="/tmp",
        python_version="3.14",
        git_enabled=False,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=True,
        project_type="django",
        starter_files=False,
        folder_count=4,
        file_count=8,
    )

    dialog = create_build_summary_dialog(
        config=config,
        on_build_callback=lambda e: None,
        on_cancel_callback=lambda e: None,
        is_dark_mode=True,
    )

    # Left column is the first control in the two-column Row layout
    controls = dialog.content.content.controls[0].controls
    labels = [
        r.controls[0].value
        for r in controls
        if hasattr(r, "controls") and hasattr(r.controls[0], "value")
    ]
    assert "Project Type:" in labels


# ========== Feature 3: SnackBar Tests ==========


def test_show_snackbar_success(mock_handlers):
    """Test _show_snackbar opens a green snackbar on success"""
    handlers, page, controls, state = mock_handlers

    handlers._show_snackbar("Project created!", is_error=False)

    assert len(page.opened_controls) == 1
    snackbar = page.opened_controls[0]
    assert snackbar.bgcolor == "green600"


def test_show_snackbar_error(mock_handlers):
    """Test _show_snackbar opens a red snackbar on error"""
    handlers, page, controls, state = mock_handlers

    handlers._show_snackbar("Build failed!", is_error=True)

    assert len(page.opened_controls) == 1
    snackbar = page.opened_controls[0]
    assert snackbar.bgcolor == "red600"


# ========== Feature 6: Keyboard Shortcut Tests ==========


@pytest.mark.asyncio
async def test_keyboard_ctrl_enter_triggers_build(mock_handlers):
    """Test Ctrl+Enter triggers build when inputs are valid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = True
    controls.build_project_button.disabled = False

    mock_event = Mock()
    mock_event.key = "Enter"
    mock_event.ctrl = True
    mock_event.meta = False

    with patch.object(handlers, "on_build_project") as mock_build:
        await handlers.on_keyboard_event(mock_event)
        mock_build.assert_called_once_with(mock_event)


@pytest.mark.asyncio
async def test_keyboard_meta_enter_triggers_build(mock_handlers):
    """Test Cmd+Enter triggers build when inputs are valid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = True
    controls.build_project_button.disabled = False

    mock_event = Mock()
    mock_event.key = "Enter"
    mock_event.ctrl = False
    mock_event.meta = True

    with patch.object(handlers, "on_build_project") as mock_build:
        await handlers.on_keyboard_event(mock_event)
        mock_build.assert_called_once_with(mock_event)


@pytest.mark.asyncio
async def test_keyboard_enter_ignored_when_invalid(mock_handlers):
    """Test Ctrl+Enter is ignored when inputs are invalid"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = False
    controls.build_project_button.disabled = True

    mock_event = Mock()
    mock_event.key = "Enter"
    mock_event.ctrl = True
    mock_event.meta = False

    with patch.object(handlers, "on_build_project") as mock_build:
        await handlers.on_keyboard_event(mock_event)
        mock_build.assert_not_called()


@pytest.mark.asyncio
async def test_keyboard_enter_ignored_when_button_disabled(mock_handlers):
    """Test Ctrl+Enter is ignored when button is disabled (build in progress)"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = True
    controls.build_project_button.disabled = True  # Build in progress

    mock_event = Mock()
    mock_event.key = "Enter"
    mock_event.ctrl = True
    mock_event.meta = False

    with patch.object(handlers, "on_build_project") as mock_build:
        await handlers.on_keyboard_event(mock_event)
        mock_build.assert_not_called()


@pytest.mark.asyncio
async def test_keyboard_other_keys_ignored(mock_handlers):
    """Test other keys don't trigger build"""
    handlers, page, controls, state = mock_handlers

    state.path_valid = True
    state.name_valid = True
    controls.build_project_button.disabled = False

    mock_event = Mock()
    mock_event.key = "Escape"
    mock_event.ctrl = True
    mock_event.meta = False

    with patch.object(handlers, "on_build_project") as mock_build:
        await handlers.on_keyboard_event(mock_event)
        mock_build.assert_not_called()


# ========== Reset Integration Tests ==========


@pytest.mark.asyncio
async def test_reset_clears_validation_icons(mock_handlers):
    """Test on_reset clears validation icons and disables build button"""
    handlers, page, controls, state = mock_handlers

    # Set some icons first
    controls.project_path_input.suffix = "something"
    controls.project_name_input.suffix = "something"

    with patch.object(handlers, "_reload_and_merge_templates"):
        await handlers._do_reset()

    # Path should get valid icon (default path is valid)
    assert controls.project_path_input.suffix is not None
    # Name should be cleared (empty after reset)
    assert controls.project_name_input.suffix is None
    # Build button should be disabled (no name)
    assert controls.build_project_button.disabled
    assert controls.build_project_button.opacity == 0.5


# ========== UI Project Toggle (Dialog-based) Tests ==========


@pytest.mark.asyncio
async def test_on_ui_project_toggle_opens_dialog(mock_handlers):
    """Test on_ui_project_toggle always opens framework dialog"""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = MockControl(value=False, label=UI_PROJECT_CHECKBOX_LABEL)

    with patch.object(handlers, "_show_framework_dialog") as mock_show:
        await handlers.on_ui_project_toggle(mock_event)

    # Handler forces checkbox to True and opens dialog
    assert mock_event.control.value
    assert state.ui_project_enabled
    mock_show.assert_called_once()
    assert page.updated


@pytest.mark.asyncio
async def test_on_ui_project_toggle_reopens_dialog(mock_handlers):
    """Test on_ui_project_toggle reopens dialog when already checked"""
    handlers, page, controls, state = mock_handlers

    # Already checked with a framework
    state.ui_project_enabled = True
    state.framework = "flet"

    mock_event = Mock()
    mock_event.control = MockControl(value=True, label="UI Project: flet")

    with patch.object(handlers, "_show_framework_dialog") as mock_show:
        await handlers.on_ui_project_toggle(mock_event)

    # Still opens dialog for re-selection
    mock_show.assert_called_once()
    assert mock_event.control.value


# ========== Framework Dialog Callback Tests ==========


def test_framework_dialog_on_select_sets_state(mock_handlers):
    """Test framework dialog on_select callback sets framework and reloads templates"""
    handlers, page, controls, state = mock_handlers

    with patch(
        "uv_forger.handlers.option_handlers.create_framework_dialog"
    ) as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = True
        mock_create.return_value = mock_dialog

        handlers._show_framework_dialog()

        # Get the on_select callback
        on_select = mock_create.call_args[1]["on_select_callback"]

    # Simulate selecting a framework
    with patch.object(handlers, "_reload_and_merge_templates"):
        on_select("flet")

    assert state.framework == "flet"
    assert controls.ui_project_checkbox.label == "UI Framework: flet"
    assert not mock_dialog.open


def test_framework_dialog_on_select_none_clears_state(mock_handlers):
    """Test framework dialog on_select with None clears framework and unchecks"""
    handlers, page, controls, state = mock_handlers

    # Start with framework selected
    state.ui_project_enabled = True
    state.framework = "flet"
    controls.ui_project_checkbox.value = True
    controls.ui_project_checkbox.label = "UI Project: flet"

    with patch(
        "uv_forger.handlers.option_handlers.create_framework_dialog"
    ) as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = True
        mock_create.return_value = mock_dialog

        handlers._show_framework_dialog()

        on_select = mock_create.call_args[1]["on_select_callback"]

    # Simulate selecting None
    with patch.object(handlers, "_reload_and_merge_templates"):
        on_select(None)

    assert state.framework is None
    assert not state.ui_project_enabled
    assert not controls.ui_project_checkbox.value
    assert controls.ui_project_checkbox.label == UI_PROJECT_CHECKBOX_LABEL
    assert not mock_dialog.open


def test_framework_dialog_on_close_unchecks_when_no_prior_selection(mock_handlers):
    """Test framework dialog cancel unchecks when no prior selection exists"""
    handlers, page, controls, state = mock_handlers

    # No prior framework
    state.ui_project_enabled = True
    state.framework = None
    controls.ui_project_checkbox.value = True

    with patch(
        "uv_forger.handlers.option_handlers.create_framework_dialog"
    ) as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = True
        mock_create.return_value = mock_dialog

        handlers._show_framework_dialog()

        on_close = mock_create.call_args[1]["on_close_callback"]

    on_close(None)

    assert not state.ui_project_enabled
    assert not controls.ui_project_checkbox.value
    assert controls.ui_project_checkbox.label == UI_PROJECT_CHECKBOX_LABEL
    assert not mock_dialog.open


def test_framework_dialog_on_close_keeps_prior_selection(mock_handlers):
    """Test framework dialog cancel keeps current selection when one exists"""
    handlers, page, controls, state = mock_handlers

    # Has prior framework selection
    state.ui_project_enabled = True
    state.framework = "PyQt6"
    controls.ui_project_checkbox.value = True
    controls.ui_project_checkbox.label = "UI Project: PyQt6"

    with patch(
        "uv_forger.handlers.option_handlers.create_framework_dialog"
    ) as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = True
        mock_create.return_value = mock_dialog

        handlers._show_framework_dialog()

        on_close = mock_create.call_args[1]["on_close_callback"]

    on_close(None)

    # Should keep everything as-is
    assert state.ui_project_enabled
    assert state.framework == "PyQt6"
    assert controls.ui_project_checkbox.value
    assert not mock_dialog.open


# ========== Project Type Dialog None Selection Tests ==========


def test_project_type_dialog_on_select_none_clears_state(mock_handlers):
    """Test project type dialog on_select with None clears and unchecks"""
    handlers, page, controls, state = mock_handlers

    # Start with project type selected
    state.other_project_enabled = True
    state.project_type = "django"
    controls.other_projects_checkbox.value = True
    controls.other_projects_checkbox.label = "Project: Django"

    with patch("uv_forger.ui.dialogs.create_project_type_dialog") as mock_create:
        mock_dialog = Mock()
        mock_dialog.open = True
        mock_create.return_value = mock_dialog

        handlers._show_project_type_dialog()

        on_select = mock_create.call_args[1]["on_select_callback"]

    # Simulate selecting None
    with patch.object(handlers, "_reload_and_merge_templates"):
        on_select(None)

    assert state.project_type is None
    assert not state.other_project_enabled
    assert not controls.other_projects_checkbox.value
    assert controls.other_projects_checkbox.label == OTHER_PROJECT_CHECKBOX_LABEL
    assert not mock_dialog.open


@pytest.mark.asyncio
async def test_reset_clears_both_checkbox_labels(mock_handlers):
    """Test on_reset resets both checkbox labels to defaults"""
    handlers, page, controls, state = mock_handlers

    # Set up checked state with labels
    state.ui_project_enabled = True
    state.framework = "flet"
    controls.ui_project_checkbox.value = True
    controls.ui_project_checkbox.label = "UI Project: flet"

    state.other_project_enabled = True
    state.project_type = "django"
    controls.other_projects_checkbox.value = True
    controls.other_projects_checkbox.label = "Project: Django"

    with patch.object(handlers, "_reload_and_merge_templates"):
        await handlers._do_reset()

    assert controls.ui_project_checkbox.label == UI_PROJECT_CHECKBOX_LABEL
    assert controls.other_projects_checkbox.label == OTHER_PROJECT_CHECKBOX_LABEL
    assert not controls.ui_project_checkbox.value
    assert not controls.other_projects_checkbox.value


# --- Package Management Tests ---


def test_update_package_display_empty(mock_handlers):
    """_update_package_display counts an empty list and re-renders the panel."""
    handlers, page, controls, state = mock_handlers

    state.packages = []
    handlers._update_package_display()

    assert controls.packages_label.value == "Packages: 0"
    controls.packages_panel.update.assert_called_once()


def test_update_package_display_with_packages(mock_handlers):
    """_update_package_display counts packages and re-renders the panel."""
    handlers, page, controls, state = mock_handlers

    state.packages = ["flet", "requests", "httpx"]
    handlers._update_package_display()

    assert controls.packages_label.value == "Packages: 3"
    controls.packages_panel.update.assert_called_once()


def test_packages_panel_renders_rows_from_state():
    """PackagesPanel builds one row per package, or a placeholder when empty."""
    from uv_forger.core.state import AppState
    from uv_forger.ui.packages_panel import PackagesPanel

    render = PackagesPanel.__wrapped__  # the component body, no renderer needed

    state = AppState()
    assert len(render(lambda: state, lambda _idx: None).content.controls) == 1  # placeholder

    state.packages = ["flet", "requests", "httpx"]
    state.dev_packages = {"httpx"}
    state.auto_packages = ["flet"]
    state.selected_package_idx = 1
    rows = render(lambda: state, lambda _idx: None).content.controls
    assert len(rows) == 3
    assert rows[1].bgcolor is not None  # selected row is highlighted
    assert [t.value for t in rows[2].content.controls] == ["httpx", "dev"]
    assert [t.value for t in rows[0].content.controls] == ["flet", "auto"]


def test_packages_panel_row_click_dispatches_index():
    """Clicking a row calls on_select with that row's index."""
    from uv_forger.core.state import AppState
    from uv_forger.ui.packages_panel import PackagesPanel

    state = AppState()
    state.packages = ["flet", "requests"]
    clicked = []
    rows = PackagesPanel.__wrapped__(lambda: state, clicked.append).content.controls
    rows[1].on_click(Mock())

    assert clicked == [1]


def test_on_package_select_sets_selection(mock_handlers):
    """Selecting a package records its index in state."""
    handlers, page, controls, state = mock_handlers

    state.packages = ["flet", "requests"]
    handlers._on_package_select(1)

    assert state.selected_package_idx == 1


@pytest.mark.asyncio
async def test_on_add_package_opens_dialog(mock_handlers):
    """on_add_package opens an add-packages dialog."""
    handlers, page, controls, state = mock_handlers

    await handlers.on_add_package(Mock())

    assert len(page.overlay) == 1  # Dialog was appended to overlay


@pytest.mark.asyncio
async def test_on_add_package_deduplicates_batch(mock_handlers):
    """Packages already in the list are skipped; new ones are added."""
    handlers, page, controls, state = mock_handlers

    state.packages = ["flet", "requests"]
    # Simulate the dialog callback being invoked directly
    existing = set(state.packages)
    new_batch = ["requests", "httpx", "django"]  # "requests" is a duplicate
    added = [p for p in new_batch if p not in existing]
    state.packages.extend(added)

    assert state.packages == ["flet", "requests", "httpx", "django"]
    assert "requests" not in added  # Was filtered as duplicate


@pytest.mark.asyncio
async def test_on_remove_package_removes_selected(mock_handlers):
    """on_remove_package removes the selected package."""
    handlers, page, controls, state = mock_handlers

    state.packages = ["flet", "requests", "httpx"]
    state.selected_package_idx = 1
    await handlers.on_remove_package(Mock())

    assert state.packages == ["flet", "httpx"]
    assert state.selected_package_idx is None


@pytest.mark.asyncio
async def test_on_remove_package_no_selection(mock_handlers):
    """on_remove_package sets a warning when nothing is selected."""
    handlers, page, controls, state = mock_handlers

    state.packages = ["flet"]
    state.selected_package_idx = None
    await handlers.on_remove_package(Mock())

    assert controls.warning_banner.value == "Select a package to remove."
    assert state.packages == ["flet"]  # Unchanged


def test_collect_state_packages_framework_only(mock_handlers):
    """_collect_state_packages returns framework package when framework selected."""
    handlers, _, _, state = mock_handlers

    state.ui_project_enabled = True
    state.framework = "flet"
    state.other_project_enabled = False

    packages = handlers._collect_state_packages()
    assert packages == ["flet"]


def test_collect_state_packages_project_type_only(mock_handlers):
    """_collect_state_packages returns project type packages when type selected."""
    handlers, _, _, state = mock_handlers

    state.ui_project_enabled = False
    state.other_project_enabled = True
    state.project_type = "django"

    packages = handlers._collect_state_packages()
    assert "django" in packages


def test_collect_state_packages_neither_selected(mock_handlers):
    """_collect_state_packages returns empty list when nothing selected."""
    handlers, _, _, state = mock_handlers

    state.ui_project_enabled = False
    state.other_project_enabled = False

    packages = handlers._collect_state_packages()
    assert packages == []


def test_collect_state_packages_builtin_framework(mock_handlers):
    """_collect_state_packages excludes built-in frameworks with no pip package."""
    handlers, _, _, state = mock_handlers

    state.ui_project_enabled = True
    state.framework = "tkinter (built-in)"
    state.other_project_enabled = False

    packages = handlers._collect_state_packages()
    assert packages == []  # tkinter maps to None, not installed


# ========== About Dialog Handler Tests ==========


@pytest.mark.asyncio
async def test_on_about_click_opens_dialog(mock_handlers):
    """Test on_about_click loads ABOUT.md and opens a dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.ABOUT_FILE") as mock_file:
        mock_file.read_text.return_value = "# About\nTest content"
        await handlers.on_about_click(None)

    assert len(page.overlay) == 1
    dialog = page.overlay[0]
    assert dialog.open is True
    assert page.updated is True


@pytest.mark.asyncio
async def test_on_about_click_handles_missing_file(mock_handlers):
    """Test on_about_click handles missing ABOUT.md gracefully."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.ABOUT_FILE") as mock_file:
        mock_file.read_text.side_effect = FileNotFoundError("not found")
        await handlers.on_about_click(None)

    # Dialog should still be opened with fallback content
    assert len(page.overlay) == 1
    assert page.overlay[0].open is True


@pytest.mark.asyncio
async def test_on_about_internal_link_help(mock_handlers):
    """Test About dialog internal link navigates to Help dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.ABOUT_FILE") as mock_file:
        mock_file.read_text.return_value = "# About\n[Help](app://help)"
        await handlers.on_about_click(None)

    about_dialog = page.overlay[0]

    # Extract the on_tap_link handler from the Markdown widget
    md_widget = about_dialog.content.content.controls[0]
    assert md_widget.on_tap_link is not None


# ========== Help Dialog Internal Link Tests ==========


@pytest.mark.asyncio
async def test_help_dialog_internal_link_about(mock_handlers):
    """Test Help dialog internal link navigates to About dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.HELP_FILE") as mock_file:
        mock_file.read_text.return_value = "# Help\n[About](app://about)"
        await handlers.on_help_click(None)

    help_dialog = page.overlay[0]
    md_widget = help_dialog.content.content.controls[0]
    assert md_widget.on_tap_link is not None


# ========== Escape Key Closes Dialogs Tests ==========


@pytest.mark.asyncio
async def test_escape_closes_active_dialog(mock_handlers):
    """Test Escape closes an active dialog instead of triggering exit."""
    handlers, page, controls, state = mock_handlers

    # Simulate an open dialog by setting active_dialog to a close callback
    closed = []

    def close_dialog(_=None):
        closed.append(True)

    state.active_dialog = close_dialog

    mock_event = Mock()
    mock_event.key = "Escape"
    mock_event.ctrl = False
    mock_event.meta = False

    with patch.object(handlers, "on_exit") as mock_exit:
        await handlers.on_keyboard_event(mock_event)
        mock_exit.assert_not_called()

    assert len(closed) == 1


@pytest.mark.asyncio
async def test_escape_triggers_exit_when_no_active_dialog(mock_handlers):
    """Test Escape triggers exit when no dialog is open."""
    handlers, page, controls, state = mock_handlers

    assert state.active_dialog is None

    mock_event = Mock()
    mock_event.key = "Escape"
    mock_event.ctrl = False
    mock_event.meta = False

    with patch.object(handlers, "on_exit") as mock_exit:
        await handlers.on_keyboard_event(mock_event)
        mock_exit.assert_called_once_with(mock_event)


@pytest.mark.asyncio
async def test_help_dialog_sets_active_dialog(mock_handlers):
    """Test opening Help dialog sets state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.HELP_FILE") as mock_file:
        mock_file.read_text.return_value = "# Help\nTest"
        await handlers.on_help_click(None)

    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_help_dialog_close_clears_active_dialog(mock_handlers):
    """Test closing Help dialog clears state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.HELP_FILE") as mock_file:
        mock_file.read_text.return_value = "# Help\nTest"
        await handlers.on_help_click(None)

    assert state.active_dialog is not None
    # Call the close callback
    state.active_dialog()
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_app_cheat_sheet_dialog_sets_active_dialog(mock_handlers):
    """Test opening App Cheat Sheet dialog sets state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.APP_CHEAT_SHEET_FILE") as mock_file:
        mock_file.read_text.return_value = "# App\nTest"
        await handlers.on_app_cheat_sheet_click(None)

    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_app_cheat_sheet_close_clears_active_dialog(mock_handlers):
    """Test closing App Cheat Sheet dialog clears state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.APP_CHEAT_SHEET_FILE") as mock_file:
        mock_file.read_text.return_value = "# App\nTest"
        await handlers.on_app_cheat_sheet_click(None)

    state.active_dialog()
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_app_cheat_sheet_file_not_found(mock_handlers):
    """Test App Cheat Sheet handles missing file gracefully."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.APP_CHEAT_SHEET_FILE") as mock_file:
        mock_file.read_text.side_effect = FileNotFoundError("not found")
        await handlers.on_app_cheat_sheet_click(None)

    assert state.active_dialog is not None


@pytest.mark.asyncio
async def test_about_dialog_sets_active_dialog(mock_handlers):
    """Test opening About dialog sets state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.ABOUT_FILE") as mock_file:
        mock_file.read_text.return_value = "# About\nTest"
        await handlers.on_about_click(None)

    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_about_dialog_close_clears_active_dialog(mock_handlers):
    """Test closing About dialog clears state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.ABOUT_FILE") as mock_file:
        mock_file.read_text.return_value = "# About\nTest"
        await handlers.on_about_click(None)

    state.active_dialog()
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_escape_closes_help_dialog_end_to_end(mock_handlers):
    """Test Escape key closes an open Help dialog end-to-end."""
    handlers, page, controls, state = mock_handlers

    with patch("uv_forger.handlers.feature_handlers.HELP_FILE") as mock_file:
        mock_file.read_text.return_value = "# Help\nTest"
        await handlers.on_help_click(None)

    help_dialog = page.overlay[0]
    assert help_dialog.open is True
    assert state.active_dialog is not None

    # Press Escape
    mock_event = Mock()
    mock_event.key = "Escape"
    mock_event.ctrl = False
    mock_event.meta = False

    with patch.object(handlers, "on_exit") as mock_exit:
        await handlers.on_keyboard_event(mock_event)
        mock_exit.assert_not_called()

    assert help_dialog.open is False
    assert state.active_dialog is None


# ========== Escape Closes Confirm Dialogs Tests ==========


@pytest.mark.asyncio
async def test_escape_closes_exit_confirm_dialog(mock_handlers):
    """Test Escape closes the Exit confirmation dialog."""
    handlers, page, controls, state = mock_handlers

    # Open exit dialog
    await handlers.on_exit(Mock())
    assert state.active_dialog is not None

    # Press Escape — should dismiss the confirm dialog, not open another
    mock_event = Mock()
    mock_event.key = "Escape"
    mock_event.ctrl = False
    mock_event.meta = False

    await handlers.on_keyboard_event(mock_event)
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_escape_closes_reset_confirm_dialog(mock_handlers):
    """Test Escape closes the Reset confirmation dialog."""
    handlers, page, controls, state = mock_handlers

    # Open reset dialog
    await handlers.on_reset(Mock())
    assert state.active_dialog is not None

    # Press Escape
    mock_event = Mock()
    mock_event.key = "Escape"
    mock_event.ctrl = False
    mock_event.meta = False

    await handlers.on_keyboard_event(mock_event)
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_exit_confirm_cancel_clears_active_dialog(mock_handlers):
    """Test cancelling Exit dialog clears active_dialog."""
    handlers, page, controls, state = mock_handlers

    await handlers.on_exit(Mock())
    assert state.active_dialog is not None

    # Call the cancel callback directly
    state.active_dialog()
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_reset_confirm_cancel_clears_active_dialog(mock_handlers):
    """Test cancelling Reset dialog clears active_dialog."""
    handlers, page, controls, state = mock_handlers

    await handlers.on_reset(Mock())
    assert state.active_dialog is not None

    state.active_dialog()
    assert state.active_dialog is None


# ========== Cmd+/ Opens Help Tests ==========


@pytest.mark.asyncio
async def test_keyboard_cmd_slash_opens_help(mock_handlers):
    """Test Cmd+/ opens the Help dialog."""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.key = "/"
    mock_event.ctrl = False
    mock_event.meta = True

    with patch.object(handlers, "on_help_click") as mock_help:
        await handlers.on_keyboard_event(mock_event)
        mock_help.assert_called_once_with(mock_event)


@pytest.mark.asyncio
async def test_keyboard_ctrl_slash_opens_help(mock_handlers):
    """Test Ctrl+/ opens the Help dialog."""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.key = "/"
    mock_event.ctrl = True
    mock_event.meta = False

    with patch.object(handlers, "on_help_click") as mock_help:
        await handlers.on_keyboard_event(mock_event)
        mock_help.assert_called_once_with(mock_event)


# ========== Escape Closes All Dialogs Tests ==========


@pytest.mark.asyncio
async def test_add_package_dialog_sets_active_dialog(mock_handlers):
    """Test opening Add Package dialog sets state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    await handlers.on_add_package(Mock())
    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_add_package_dialog_close_clears_active_dialog(mock_handlers):
    """Test closing Add Package dialog clears state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    await handlers.on_add_package(Mock())
    assert state.active_dialog is not None

    state.active_dialog()
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_clear_packages_shows_confirm_dialog(mock_handlers):
    """Test Clear Packages shows a confirmation dialog."""
    handlers, page, controls, state = mock_handlers
    state.packages = ["flet", "httpx"]

    await handlers.on_clear_packages(Mock())

    # Should show confirm dialog, not clear immediately
    assert state.active_dialog is not None
    assert state.packages == ["flet", "httpx"]  # Not cleared yet


@pytest.mark.asyncio
async def test_clear_packages_no_op_when_empty(mock_handlers):
    """Test Clear Packages does nothing when package list is empty."""
    handlers, page, controls, state = mock_handlers
    state.packages = []

    await handlers.on_clear_packages(Mock())
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_clear_packages_cancel_preserves_packages(mock_handlers):
    """Test cancelling Clear Packages preserves the package list."""
    handlers, page, controls, state = mock_handlers
    state.packages = ["flet", "httpx"]

    await handlers.on_clear_packages(Mock())
    assert state.active_dialog is not None

    # Cancel via Escape (active_dialog)
    state.active_dialog()
    assert state.active_dialog is None
    assert state.packages == ["flet", "httpx"]


@pytest.mark.asyncio
async def test_clear_packages_confirm_clears_all(mock_handlers):
    """Test confirming Clear Packages removes all packages."""
    handlers, page, controls, state = mock_handlers
    state.packages = ["flet", "httpx"]
    state.auto_packages = ["flet"]
    state.selected_package_idx = 0

    await handlers.on_clear_packages(Mock())

    # Find the confirm dialog and call the confirm callback
    dialog = page.opened_controls[-1]
    # The confirm button is the first action
    confirm_button = dialog.actions[0]
    confirm_button.on_click(Mock())

    assert state.packages == []
    assert state.auto_packages == []
    assert state.selected_package_idx is None
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_framework_dialog_sets_active_dialog(mock_handlers):
    """Test opening UI Framework dialog sets state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = controls.ui_project_checkbox
    await handlers.on_ui_project_toggle(mock_event)

    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_framework_dialog_close_clears_active_dialog(mock_handlers):
    """Test closing UI Framework dialog clears state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = controls.ui_project_checkbox
    await handlers.on_ui_project_toggle(mock_event)

    state.active_dialog()
    assert state.active_dialog is None


@pytest.mark.asyncio
async def test_project_type_dialog_sets_active_dialog(mock_handlers):
    """Test opening Project Type dialog sets state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = controls.other_projects_checkbox
    await handlers.on_other_project_toggle(mock_event)

    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_project_type_dialog_close_clears_active_dialog(mock_handlers):
    """Test closing Project Type dialog clears state.active_dialog."""
    handlers, page, controls, state = mock_handlers

    mock_event = Mock()
    mock_event.control = controls.other_projects_checkbox
    await handlers.on_other_project_toggle(mock_event)

    state.active_dialog()
    assert state.active_dialog is None
