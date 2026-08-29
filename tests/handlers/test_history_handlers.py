"""Tests for history-related handlers in build_handlers and feature_handlers."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from uv_forger.core.history_manager import ProjectHistoryEntry
from uv_forger.core.state import AppState
from uv_forger.handlers.ui_handler import Handlers
from uv_forger.ui.folders_panel import FolderPanelCallbacks


class MockPage:
    def __init__(self):
        self.updated = False
        self.overlay = []
        self.snack_bar = None
        self.appbar = None
        self.bottom_appbar = Mock(bgcolor=None)
        self.theme_mode = None
        self.window = Mock()
        self.title = "UV Forger"
        self._shown_dialogs = []

    def update(self):
        self.updated = True

    def show_dialog(self, control):
        self._shown_dialogs.append(control)
        self.snack_bar = control


class MockControls:
    def __init__(self):
        self.warning_banner = Mock(value="")
        self.status_icon = Mock(visible=False)
        self.status_text = Mock(value="")
        self.section_titles = []
        self.section_containers = []
        self.project_name_input = Mock(value="", suffix=None)
        self.project_path_input = Mock(value="", suffix=None)
        self.python_version_dropdown = Mock(value="3.14")
        self.create_git_checkbox = Mock(
            value=True, label="Initialize Git Repository", label_style=None
        )
        self.include_starter_files_checkbox = Mock(
            value=True, label="Include Starter Files", label_style=None
        )
        self.ui_project_checkbox = Mock(
            value=False, label="Create UI Project", label_style=None
        )
        self.other_projects_checkbox = Mock(
            value=False, label="Create Other Project Type", label_style=None
        )
        self.save_as_preset_button = Mock()
        self.build_project_button = Mock(disabled=True, opacity=0.5, tooltip="")
        self.copy_path_button = Mock(disabled=True, opacity=0.4, tooltip="")
        self.pypi_status_text = Mock(value="")
        self.check_pypi_button = Mock(disabled=True)
        self.path_preview_text = Mock(value="\u00a0")
        self.progress_ring = Mock(visible=False)
        self.progress_bar = Mock(visible=False, value=0)
        self.progress_step_text = Mock(visible=False, value="")
        self.app_subfolders_label = Mock(value="App Subfolders:")
        self.packages_label = Mock(value="Packages: 0")
        self.packages_panel = Mock()
        self.folders_panel = Mock()
        self.folder_callbacks = FolderPanelCallbacks()
        self.metadata_button = Mock()
        self.metadata_summary = Mock(value="")


def _sample_folders():
    """Return folder dicts in the format _update_folder_display expects."""
    return [
        {
            "name": "core",
            "create_init": True,
            "root_level": False,
            "subfolders": [],
            "files": ["state.py"],
        },
        {
            "name": "utils",
            "create_init": True,
            "root_level": False,
            "subfolders": [],
            "files": [],
        },
    ]


def _make_entry(**kwargs):
    defaults = {
        "project_name": "test-project",
        "project_path": "/tmp/projects",
        "python_version": "3.14",
        "git_enabled": True,
        "include_starter_files": True,
        "ui_project_enabled": True,
        "framework": "Flet",
        "other_project_enabled": False,
        "project_type": None,
        "folders": _sample_folders(),
        "packages": ["httpx", "flet"],
        "built_at": "2026-02-19T10:00:00+00:00",
    }
    defaults.update(kwargs)
    return ProjectHistoryEntry(**defaults)


@pytest.fixture
def handler_setup():
    page = MockPage()
    controls = MockControls()
    state = AppState()
    handlers = Handlers(page, controls, state)
    return handlers, page, controls, state


@pytest.mark.asyncio
async def test_on_history_click_opens_dialog(handler_setup):
    """on_history_click opens a dialog via page.overlay."""
    handlers, page, controls, state = handler_setup

    with patch("uv_forger.handlers.feature_handlers.load_history", return_value=[]):
        await handlers.on_history_click(None)

    assert len(page.overlay) == 1
    assert page.updated


@pytest.mark.asyncio
async def test_on_history_click_with_entries(handler_setup):
    """on_history_click shows entries when history exists."""
    handlers, page, controls, state = handler_setup
    entry = _make_entry()

    with patch(
        "uv_forger.handlers.feature_handlers.load_history", return_value=[entry]
    ):
        await handlers.on_history_click(None)

    assert len(page.overlay) == 1
    assert page.updated


def test_restore_from_history_populates_state(handler_setup):
    """_restore_from_history sets all state fields from entry."""
    handlers, page, controls, state = handler_setup
    entry = _make_entry(
        project_name="restored-app",
        project_path="/tmp/projects",
        python_version="3.13",
        git_enabled=False,
        include_starter_files=False,
        ui_project_enabled=True,
        framework="Flet",
        other_project_enabled=True,
        project_type="FastAPI",
        packages=["flet", "fastapi"],
    )

    with patch.object(Path, "is_dir", return_value=True):
        handlers._restore_from_history(entry)

    assert state.project_name == "restored-app"
    assert state.project_path == "/tmp/projects"
    assert state.python_version == "3.13"
    assert state.git_enabled is False
    assert state.include_starter_files is False
    assert state.ui_project_enabled is True
    assert state.framework == "Flet"
    assert state.other_project_enabled is True
    assert state.project_type == "FastAPI"
    assert state.packages == ["flet", "fastapi"]


def test_restore_sets_folder_display_directly(handler_setup):
    """_restore_from_history sets folders on state without reloading templates."""
    handlers, page, controls, state = handler_setup
    custom_folders = [
        {
            "name": "custom_folder",
            "create_init": False,
            "root_level": False,
            "subfolders": [],
            "files": [],
        },
        {
            "name": "nested",
            "create_init": False,
            "root_level": False,
            "subfolders": [],
            "files": ["a.py"],
        },
    ]
    entry = _make_entry(folders=custom_folders)

    with patch.object(Path, "is_dir", return_value=True):
        handlers._restore_from_history(entry)

    assert state.folders == custom_folders


def test_restore_updates_ui_controls(handler_setup):
    """_restore_from_history updates UI control values."""
    handlers, page, controls, state = handler_setup
    entry = _make_entry(
        project_name="my-app",
        ui_project_enabled=True,
        framework="PyQt6",
        other_project_enabled=True,
        project_type="Django",
    )

    with patch.object(Path, "is_dir", return_value=True):
        handlers._restore_from_history(entry)

    assert controls.project_name_input.value == "my-app"
    assert controls.ui_project_checkbox.label == "UI Framework: PyQt6"
    assert controls.other_projects_checkbox.label == "Project Type: Django"


def test_restore_shows_snackbar(handler_setup):
    """_restore_from_history shows a snackbar with project name."""
    handlers, page, controls, state = handler_setup
    entry = _make_entry(project_name="cool-project")

    with patch.object(Path, "is_dir", return_value=True):
        handlers._restore_from_history(entry)

    assert len(page._shown_dialogs) == 1  # snackbar shown


@pytest.mark.asyncio
async def test_history_saved_after_successful_build(handler_setup):
    """Successful build calls add_to_history."""
    handlers, page, controls, state = handler_setup

    state.project_name = "build-test"
    state.project_path = "/tmp/projects"
    state.python_version = "3.14"
    state.path_valid = True
    state.name_valid = True

    mock_result = Mock(success=True, message="Project created!")

    with (
        patch(
            "uv_forger.handlers.build_handlers.AsyncExecutor.run",
            return_value=mock_result,
        ),
        patch("uv_forger.handlers.build_handlers.add_to_history") as mock_add,
        patch("uv_forger.handlers.build_handlers.make_history_entry") as mock_make,
    ):
        mock_entry = Mock()
        mock_make.return_value = mock_entry
        await handlers._execute_build()

        mock_make.assert_called_once()
        mock_add.assert_called_once_with(mock_entry)
