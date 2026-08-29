"""Tests for preset-related handlers in build_handlers and feature_handlers."""

from unittest.mock import Mock, patch

import pytest

from uv_forger.core.preset_manager import ProjectPreset
from uv_forger.core.state import AppState
from uv_forger.handlers.ui_handler import Handlers


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
        self.subfolders_container = Mock(content=Mock(controls=[]))
        self.metadata_checkbox = Mock(value=False, label_style=None)
        self.metadata_summary = Mock(value="")
        self.preset_dropdown = Mock(value="None")


def _sample_folders():
    return [
        {
            "name": "core",
            "create_init": True,
            "root_level": False,
            "subfolders": [],
            "files": ["state.py"],
        },
    ]


def _make_preset(**kwargs):
    defaults = {
        "name": "My FastAPI Stack",
        "python_version": "3.14",
        "git_enabled": True,
        "include_starter_files": True,
        "ui_project_enabled": True,
        "framework": "Flet",
        "other_project_enabled": True,
        "project_type": "FastAPI",
        "folders": _sample_folders(),
        "packages": ["flet", "fastapi"],
        "dev_packages": ["pytest"],
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "description": "My project",
        "license_type": "MIT",
        "saved_at": "2026-02-19T10:00:00+00:00",
    }
    defaults.update(kwargs)
    return ProjectPreset(**defaults)


@pytest.fixture
def handler_setup():
    page = MockPage()
    controls = MockControls()
    state = AppState()
    handlers = Handlers(page, controls, state)
    return handlers, page, controls, state


def test_apply_preset_populates_state(handler_setup):
    """_apply_preset sets all configuration state fields from preset."""
    handlers, page, controls, state = handler_setup
    preset = _make_preset()

    handlers._apply_preset(preset)

    assert state.python_version == "3.14"
    assert state.git_enabled is True
    assert state.include_starter_files is True
    assert state.ui_project_enabled is True
    assert state.framework == "Flet"
    assert state.other_project_enabled is True
    assert state.project_type == "FastAPI"
    assert state.packages == ["flet", "fastapi"]
    assert state.dev_packages == {"pytest"}
    assert state.author_name == "Alice"
    assert state.author_email == "alice@example.com"
    assert state.description == "My project"
    assert state.license_type == "MIT"


def test_apply_preset_does_not_set_project_name(handler_setup):
    """_apply_preset leaves project_name and project_path unchanged."""
    handlers, page, controls, state = handler_setup
    state.project_name = "keep-this"
    state.project_path = "/keep/this"

    handlers._apply_preset(_make_preset())

    assert state.project_name == "keep-this"
    assert state.project_path == "/keep/this"


def test_apply_preset_updates_ui_controls(handler_setup):
    """_apply_preset syncs UI controls with preset values."""
    handlers, page, controls, state = handler_setup
    preset = _make_preset(
        python_version="3.13",
        git_enabled=False,
        ui_project_enabled=True,
        framework="PyQt6",
        other_project_enabled=True,
        project_type="Django",
    )

    handlers._apply_preset(preset)

    assert controls.python_version_dropdown.value == "3.13"
    assert controls.create_git_checkbox.value is False
    assert controls.ui_project_checkbox.label == "UI Framework: PyQt6"
    assert controls.other_projects_checkbox.label == "Project Type: Django"


def test_apply_preset_sets_folders_directly(handler_setup):
    """_apply_preset sets folders on state without reloading templates."""
    handlers, page, controls, state = handler_setup
    custom_folders = [
        {
            "name": "custom",
            "create_init": False,
            "root_level": False,
            "subfolders": [],
            "files": ["x.py"],
        },
    ]
    preset = _make_preset(folders=custom_folders)

    handlers._apply_preset(preset)

    assert state.folders == custom_folders


def test_apply_preset_shows_snackbar(handler_setup):
    """_apply_preset shows a snackbar with the preset name."""
    handlers, page, controls, state = handler_setup
    preset = _make_preset(name="Cool Preset")

    handlers._apply_preset(preset)

    assert len(page._shown_dialogs) == 1


def test_apply_preset_updates_metadata_checkbox(handler_setup):
    """_apply_preset checks the metadata checkbox when metadata is present."""
    handlers, page, controls, state = handler_setup
    preset = _make_preset(author_name="Bob", license_type="Apache-2.0")

    handlers._apply_preset(preset)

    assert controls.metadata_checkbox.value is True


def test_apply_preset_unchecks_metadata_when_empty(handler_setup):
    """_apply_preset unchecks metadata checkbox when no metadata in preset."""
    handlers, page, controls, state = handler_setup
    preset = _make_preset(
        author_name="", author_email="", description="", license_type=""
    )

    handlers._apply_preset(preset)

    assert controls.metadata_checkbox.value is False


def test_save_current_as_preset(handler_setup):
    """_save_current_as_preset snapshots current state."""
    handlers, page, controls, state = handler_setup
    state.python_version = "3.13"
    state.git_enabled = False
    state.include_starter_files = True
    state.ui_project_enabled = True
    state.framework = "Flet"
    state.other_project_enabled = False
    state.project_type = None
    state.folders = [{"name": "core"}]
    state.packages = ["flet"]
    state.dev_packages = {"ruff"}
    state.author_name = "Charlie"

    with patch("uv_forger.handlers.build_handlers.add_preset") as mock_add:
        handlers._save_current_as_preset("My Preset")

        mock_add.assert_called_once()
        preset = mock_add.call_args[0][0]
        assert preset.name == "My Preset"
        assert preset.python_version == "3.13"
        assert preset.git_enabled is False
        assert preset.framework == "Flet"
        assert preset.packages == ["flet"]
        assert "ruff" in preset.dev_packages
        assert preset.author_name == "Charlie"


@pytest.mark.asyncio
async def test_on_presets_click_opens_dialog(handler_setup):
    """on_presets_click opens a dialog via page.overlay."""
    handlers, page, controls, state = handler_setup

    with patch("uv_forger.handlers.feature_handlers.load_presets", return_value=[]):
        await handlers.on_presets_click(None)

    assert len(page.overlay) == 1
    assert page.updated


@pytest.mark.asyncio
async def test_on_presets_click_with_presets(handler_setup):
    """on_presets_click shows presets when they exist."""
    handlers, page, controls, state = handler_setup
    preset = _make_preset()

    with patch(
        "uv_forger.handlers.feature_handlers.load_presets", return_value=[preset]
    ):
        await handlers.on_presets_click(None)

    assert len(page.overlay) == 1
    assert page.updated
