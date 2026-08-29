"""Tests for InputHandlersMixin — on_check_pypi and on_project_name_change."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from uv_forger.core.state import AppState
from uv_forger.handlers.ui_handler import Handlers
from uv_forger.ui.folders_panel import FolderPanelCallbacks
from uv_forger.ui.ui_config import UIConfig


class MockControl:
    def __init__(self, value=None):
        self.value = value
        self.visible = True
        self.disabled = False
        self.color = None
        self.suffix = None
        self.label_style = None
        self.opacity = 1.0
        self.tooltip = None

    async def focus(self):
        pass


class MockText:
    def __init__(self, value=""):
        self.value = value
        self.color = None


class MockContainer:
    def __init__(self):
        self.content = Mock()
        self.content.controls = []
        self.border = None


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
        self.folders_panel = Mock()
        self.folder_callbacks = FolderPanelCallbacks()
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
        self.metadata_summary = MockText()
        self.section_titles = []
        self.section_containers = []


@pytest.fixture
def mock_handlers():
    page = MockPage()
    controls = MockControls()
    state = AppState()
    state.project_name = "my_app"
    state.name_valid = True
    handlers = Handlers(page, controls, state)
    return handlers, page, controls, state


class TestOnCheckPypi:
    """Tests for InputHandlersMixin.on_check_pypi."""

    async def test_available_shows_success_message(self, mock_handlers):
        handlers, page, controls, state = mock_handlers
        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await handlers.on_check_pypi(Mock())

        assert "available" in controls.pypi_status_text.value.lower()
        assert controls.pypi_status_text.color == UIConfig.COLOR_SUCCESS

    async def test_taken_shows_error_message(self, mock_handlers):
        handlers, page, controls, state = mock_handlers
        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            new_callable=AsyncMock,
            return_value=False,
        ):
            await handlers.on_check_pypi(Mock())

        assert "taken" in controls.pypi_status_text.value.lower()
        assert controls.pypi_status_text.color == UIConfig.COLOR_ERROR

    async def test_network_error_shows_warning(self, mock_handlers):
        handlers, page, controls, state = mock_handlers
        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await handlers.on_check_pypi(Mock())

        assert controls.pypi_status_text.color == UIConfig.COLOR_WARNING

    async def test_button_disabled_during_check_then_reenabled(self, mock_handlers):
        handlers, page, controls, state = mock_handlers
        button_states = []

        async def capture_state(*_, **__):
            button_states.append(controls.check_pypi_button.disabled)
            return True

        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            side_effect=capture_state,
        ):
            await handlers.on_check_pypi(Mock())

        # During the call, button was disabled
        assert button_states == [True]
        # After the call, button is re-enabled
        assert not controls.check_pypi_button.disabled

    async def test_skips_when_name_invalid(self, mock_handlers):
        handlers, page, controls, state = mock_handlers
        state.name_valid = False

        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            new_callable=AsyncMock,
        ) as mock_check:
            await handlers.on_check_pypi(Mock())

        mock_check.assert_not_called()

    async def test_skips_when_name_empty(self, mock_handlers):
        handlers, page, controls, state = mock_handlers
        state.project_name = ""
        state.name_valid = True

        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            new_callable=AsyncMock,
        ) as mock_check:
            await handlers.on_check_pypi(Mock())

        mock_check.assert_not_called()

    async def test_normalized_name_shown_in_message(self, mock_handlers):
        """PyPI message shows normalized name (underscores → hyphens)."""
        handlers, page, controls, state = mock_handlers
        state.project_name = "my_app"

        with patch(
            "uv_forger.handlers.input_handlers.check_pypi_availability",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await handlers.on_check_pypi(Mock())

        assert "my-app" in controls.pypi_status_text.value
