#!/usr/bin/env python3
"""Pytest tests for feature_handlers.py - Log viewer, settings, and feature handlers."""

from unittest.mock import Mock, patch

import flet as ft
import pytest

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
        self.metadata_button = Mock()
        self.metadata_checkbox = Mock(value=False, label_style=None)
        self.metadata_summary = Mock(value="")
        self.section_titles = []
        self.section_containers = []


@pytest.fixture
def handler_setup():
    page = MockPage()
    controls = MockControls()
    state = AppState()
    handlers = Handlers(page, controls, state)
    return handlers, page, controls, state


@pytest.mark.asyncio
async def test_on_log_viewer_click(handler_setup, tmp_path):
    """Handler opens dialog when log file exists."""
    handlers, page, controls, state = handler_setup

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "app_2026-02-19.log"
    log_file.write_text(
        "2026-02-19 10:00:00 | INFO     | app.main:start:10 - Started\n"
    )

    with (
        patch("uv_forger.handlers.feature_handlers.LOG_DIR", tmp_path / "logs"),
        patch("uv_forger.handlers.feature_handlers.date") as mock_date,
    ):
        mock_date.today.return_value = type(
            "D", (), {"__format__": lambda self, fmt: "2026-02-19"}
        )()
        await handlers.on_log_viewer_click(None)

    assert len(page.overlay) == 1
    assert isinstance(page.overlay[0], ft.AlertDialog)
    assert page.overlay[0].open is True
    assert state.active_dialog is not None


@pytest.mark.asyncio
async def test_on_log_viewer_click_no_file(handler_setup, tmp_path):
    """Handler shows snackbar when no log file exists."""
    handlers, page, controls, state = handler_setup

    with (
        patch("uv_forger.handlers.feature_handlers.LOG_DIR", tmp_path / "logs"),
        patch("uv_forger.handlers.feature_handlers.date") as mock_date,
    ):
        mock_date.today.return_value = type(
            "D", (), {"__format__": lambda self, fmt: "2026-02-19"}
        )()
        await handlers.on_log_viewer_click(None)

    # No dialog opened
    assert len(page.overlay) == 0
    # Snackbar shown
    assert page.snack_bar is not None


def test_open_file_in_ide(handler_setup, tmp_path):
    """_open_file_in_ide launches subprocess for existing file."""
    handlers, page, controls, state = handler_setup
    state.settings.preferred_ide = "VS Code"

    # Create the target file
    mod_dir = tmp_path / "uv_forger" / "core"
    mod_dir.mkdir(parents=True)
    (mod_dir / "state.py").write_text("# state")

    with (
        patch("uv_forger.handlers.feature_handlers._APP_ROOT", tmp_path),
        patch("uv_forger.handlers.feature_handlers.subprocess") as mock_sub,
    ):
        handlers._open_file_in_ide("uv_forger.core.state", 42)

    mock_sub.Popen.assert_called_once()


def test_open_file_in_ide_missing_file(handler_setup, tmp_path):
    """_open_file_in_ide does nothing for non-existent file."""
    handlers, page, controls, state = handler_setup

    with (
        patch("uv_forger.handlers.feature_handlers._APP_ROOT", tmp_path),
        patch("uv_forger.handlers.feature_handlers.subprocess") as mock_sub,
    ):
        handlers._open_file_in_ide("app.nonexistent.module", 1)

    mock_sub.Popen.assert_not_called()


# ========== Metadata Handler Tests ==========


@pytest.mark.asyncio
async def test_on_metadata_toggle_opens_dialog(handler_setup):
    """Test on_metadata_toggle opens a metadata dialog."""
    handlers, page, controls, state = handler_setup
    mock_event = Mock()
    mock_event.control = controls.metadata_checkbox

    await handlers.on_metadata_toggle(mock_event)

    assert len(page.overlay) == 1
    assert isinstance(page.overlay[0], ft.AlertDialog)
    assert page.overlay[0].open is True
    assert state.active_dialog is not None


@pytest.mark.asyncio
async def test_on_metadata_toggle_sets_active_dialog(handler_setup):
    """Test opening metadata dialog sets state.active_dialog."""
    handlers, page, controls, state = handler_setup
    mock_event = Mock()
    mock_event.control = controls.metadata_checkbox

    await handlers.on_metadata_toggle(mock_event)

    assert state.active_dialog is not None
    assert callable(state.active_dialog)


@pytest.mark.asyncio
async def test_on_metadata_close_clears_active_dialog(handler_setup):
    """Test closing metadata dialog clears state.active_dialog."""
    handlers, page, controls, state = handler_setup
    mock_event = Mock()
    mock_event.control = controls.metadata_checkbox

    await handlers.on_metadata_toggle(mock_event)
    assert state.active_dialog is not None

    state.active_dialog()
    assert state.active_dialog is None


def test_update_metadata_summary_with_author_and_license(handler_setup):
    """Test _update_metadata_summary shows author and license."""
    handlers, page, controls, state = handler_setup

    state.author_name = "Tim"
    state.license_type = "MIT"
    handlers._update_metadata_summary()

    assert controls.metadata_summary.value == "Tim | MIT"


def test_update_metadata_summary_author_only(handler_setup):
    """Test _update_metadata_summary shows author only."""
    handlers, page, controls, state = handler_setup

    state.author_name = "Tim"
    state.license_type = ""
    handlers._update_metadata_summary()

    assert controls.metadata_summary.value == "Tim"


def test_update_metadata_summary_license_only(handler_setup):
    """Test _update_metadata_summary shows license only."""
    handlers, page, controls, state = handler_setup

    state.author_name = ""
    state.license_type = "MIT"
    handlers._update_metadata_summary()

    assert controls.metadata_summary.value == "MIT"


def test_update_metadata_summary_empty(handler_setup):
    """Test _update_metadata_summary is empty when no metadata."""
    handlers, page, controls, state = handler_setup

    state.author_name = ""
    state.license_type = ""
    handlers._update_metadata_summary()

    assert controls.metadata_summary.value == ""
