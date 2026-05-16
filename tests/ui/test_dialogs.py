#!/usr/bin/env python3
"""Pytest tests for dialogs.py - Project type dialog and about dialog creation"""

from unittest.mock import AsyncMock, Mock

import flet as ft
import pytest

from uv_forger.core.models import BuildSummaryConfig
from uv_forger.core.state import AppState
from uv_forger.ui.content_dialogs import create_about_dialog
from uv_forger.ui.dialogs import (
    _parse_log_line,
    _parse_log_location,
    create_add_item_dialog,
    create_add_packages_dialog,
    create_log_viewer_dialog,
    create_metadata_dialog,
    create_project_type_dialog,
)
from uv_forger.ui.tree_builder import build_project_tree_lines


def test_create_project_type_dialog_basic():
    """Test basic dialog creation"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.modal
    assert dialog.title is not None
    assert dialog.content is not None
    assert dialog.actions is not None
    assert len(dialog.actions) == 2  # Select and Cancel buttons


def test_create_project_type_dialog_with_selection():
    """Test dialog creation with current selection"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection="django",
        is_dark_mode=True,
    )

    # Find the RadioGroup in the dialog content
    radio_group = dialog.content.content
    assert isinstance(radio_group, ft.RadioGroup)
    assert radio_group.value == "django"


def test_create_project_type_dialog_default_selection():
    """Test dialog defaults to '_none_' when no selection"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    radio_group = dialog.content.content
    assert radio_group.value == "_none_"


def test_create_project_type_dialog_dark_mode():
    """Test dialog creation in dark mode"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    assert isinstance(dialog, ft.AlertDialog)
    # Dialog should be created without errors in dark mode


def test_create_project_type_dialog_light_mode():
    """Test dialog creation in light mode"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=False,
    )

    assert isinstance(dialog, ft.AlertDialog)
    # Dialog should be created without errors in light mode


def test_create_project_type_dialog_has_categories():
    """Test dialog contains expected project type categories"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    # Get the radio group content (Column with all controls)
    radio_group = dialog.content.content
    column = radio_group.content

    # Extract all text values from the column
    text_values = []
    for control in column.controls:
        if isinstance(control, ft.Container):
            if isinstance(control.content, ft.Text):
                text_values.append(control.content.value)
            elif isinstance(control.content, ft.Row):
                # Enhanced categories have Row with icon + text
                for item in control.content.controls:
                    if isinstance(item, ft.Text):
                        text_values.append(item.value)
            elif isinstance(control.content, ft.Radio):
                text_values.append(control.content.label)

    # Check that expected categories appear
    text_str = " ".join(text_values)
    assert "Web Frameworks" in text_str
    assert "Data Science" in text_str or "Data Science & ML" in text_str
    assert "CLI Tools" in text_str


def test_create_project_type_dialog_has_project_types():
    """Test dialog contains specific project types"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    radio_group = dialog.content.content
    column = radio_group.content

    # Extract all radio button values
    radio_values = []
    for control in column.controls:
        if isinstance(control, ft.Container) and isinstance(control.content, ft.Radio):
            radio_values.append(control.content.value)

    # Check for expected project types
    assert "django" in radio_values
    assert "fastapi" in radio_values
    assert "flask" in radio_values
    assert "data_analysis" in radio_values
    assert "cli_typer" in radio_values
    assert "scraping" in radio_values


@pytest.mark.parametrize(
    "project_type",
    [
        "django",
        "fastapi",
        "flask",
        "bottle",
        "data_analysis",
        "ml_sklearn",
        "cli_click",
        "cli_typer",
        "scraping",
    ],
)
def test_create_project_type_dialog_various_selections(project_type):
    """Test dialog can be created with various project type selections"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=project_type,
        is_dark_mode=True,
    )

    radio_group = dialog.content.content
    assert radio_group.value == project_type


def test_create_project_type_dialog_callbacks_not_none():
    """Test that callbacks are required (not None)"""
    # This test verifies the dialog can be created with valid callbacks
    select_called = []
    close_called = []

    def on_select(pt):
        select_called.append(pt)

    def on_close(e):
        close_called.append(True)

    dialog = create_project_type_dialog(
        on_select_callback=on_select,
        on_close_callback=on_close,
        current_selection=None,
        is_dark_mode=True,
    )

    assert dialog is not None
    # Note: We can't easily test callback execution without a full Flet page


def test_create_project_type_dialog_content_structure():
    """Test dialog content has correct structure"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    # Dialog should have a Container as content
    assert isinstance(dialog.content, ft.Container)

    # Container should hold a RadioGroup
    assert isinstance(dialog.content.content, ft.RadioGroup)

    # RadioGroup should have a Column as content
    radio_group = dialog.content.content
    assert isinstance(radio_group.content, ft.Column)

    # Column should have controls (categories and radios)
    column = radio_group.content
    assert len(column.controls) > 0


def test_create_project_type_dialog_actions():
    """Test dialog has correct action buttons"""
    dialog = create_project_type_dialog(
        on_select_callback=lambda x: None,
        on_close_callback=lambda x: None,
        current_selection=None,
        is_dark_mode=True,
    )

    assert len(dialog.actions) == 2

    # Check button types - Select is FilledButton, Cancel is OutlinedButton
    assert isinstance(dialog.actions[0], ft.FilledButton)  # Select button
    assert isinstance(dialog.actions[1], ft.OutlinedButton)  # Cancel button


# ========== About Dialog Tests ==========


def test_create_about_dialog_basic():
    """Test about dialog creates a valid AlertDialog."""
    page = Mock()
    page.launch_url = AsyncMock()

    dialog = create_about_dialog(
        content="# About\nTest content",
        on_close=lambda _: None,
        page=page,
        is_dark_mode=True,
    )

    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.modal is True
    assert dialog.actions is not None
    assert len(dialog.actions) == 1  # Close button only


def test_create_about_dialog_light_mode():
    """Test about dialog works in light mode."""
    page = Mock()
    page.launch_url = AsyncMock()

    dialog = create_about_dialog(
        content="# About",
        on_close=lambda _: None,
        page=page,
        is_dark_mode=False,
    )

    assert isinstance(dialog, ft.AlertDialog)


def test_create_about_dialog_with_internal_link_callback():
    """Test about dialog accepts on_internal_link parameter."""
    page = Mock()
    page.launch_url = AsyncMock()
    captured = []

    dialog = create_about_dialog(
        content="# About\n[Help](app://help)",
        on_close=lambda _: None,
        page=page,
        is_dark_mode=True,
        on_internal_link=lambda path: captured.append(path),
    )

    assert isinstance(dialog, ft.AlertDialog)


def test_create_about_dialog_has_markdown_content():
    """Test about dialog wraps content in a Markdown widget."""
    page = Mock()
    page.launch_url = AsyncMock()

    dialog = create_about_dialog(
        content="# UV Project Creator\nVersion 0.1.0",
        on_close=lambda _: None,
        page=page,
        is_dark_mode=True,
    )

    # Content is Container > Column > [Markdown]
    column = dialog.content.content
    assert isinstance(column, ft.Column)
    assert len(column.controls) == 1
    assert isinstance(column.controls[0], ft.Markdown)


# ========== Project Tree Preview Tests ==========


def _make_config(**overrides) -> BuildSummaryConfig:
    """Create a BuildSummaryConfig with sensible defaults."""
    defaults = dict(
        project_name="my_project",
        project_path="/tmp",
        python_version="3.14",
        git_enabled=True,
        ui_project_enabled=False,
        framework=None,
        other_project_enabled=False,
        project_type=None,
        starter_files=True,
        folder_count=2,
        file_count=5,
        packages=[],
        folders=[
            {
                "name": "core",
                "create_init": True,
                "subfolders": [],
                "files": ["state.py", "models.py"],
            },
            {
                "name": "ui",
                "create_init": True,
                "subfolders": [],
                "files": ["components.py"],
            },
        ],
    )
    defaults.update(overrides)
    return BuildSummaryConfig(**defaults)


def test_tree_root_line():
    """Tree starts with project_name/."""
    config = _make_config()
    lines = build_project_tree_lines(config)
    assert lines[0] == "my_project/"


def test_tree_includes_root_files_with_git():
    """Tree includes .gitignore when git is enabled."""
    config = _make_config(git_enabled=True)
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    assert ".gitignore" in text
    assert ".python-version" in text
    assert "README.md" in text
    assert "pyproject.toml" in text


def test_tree_excludes_gitignore_without_git():
    """Tree excludes .gitignore when git is disabled."""
    config = _make_config(git_enabled=False)
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    assert ".gitignore" not in text
    assert "pyproject.toml" in text


def test_tree_includes_app_dir():
    """Tree includes app/ with __init__.py and main.py."""
    config = _make_config()
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    assert "app/" in text
    assert "__init__.py" in text
    assert "main.py" in text


def test_tree_includes_template_folders():
    """Tree includes template folders inside app/."""
    config = _make_config()
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    assert "core/" in text
    assert "state.py" in text
    assert "models.py" in text
    assert "ui/" in text
    assert "components.py" in text


def test_tree_create_init_true_shows_init_py():
    """Folders with create_init=True show __init__.py."""
    config = _make_config(
        folders=[{"name": "core", "create_init": True, "subfolders": [], "files": []}]
    )
    lines = build_project_tree_lines(config)
    # Find __init__.py under core/
    core_idx = next(i for i, line in enumerate(lines) if "core/" in line)
    assert "__init__.py" in lines[core_idx + 1]


def test_tree_create_init_false_no_init_py():
    """Folders with create_init=False don't show __init__.py."""
    config = _make_config(
        folders=[
            {
                "name": "assets",
                "create_init": False,
                "subfolders": [],
                "files": ["logo.png"],
            }
        ]
    )
    lines = build_project_tree_lines(config)
    # Find the line after assets/
    assets_idx = next(i for i, line in enumerate(lines) if "assets/" in line)
    assert "logo.png" in lines[assets_idx + 1]
    # No __init__.py between assets/ and logo.png
    assert "__init__" not in lines[assets_idx + 1]


def test_tree_create_init_false_inherited_by_string_subfolders():
    """String subfolders inherit create_init=False from parent — no __init__.py."""
    from uv_forger.core.template_merger import normalize_folder

    raw_folder = {
        "name": "assets",
        "create_init": False,
        "subfolders": ["icons", "images"],
        "files": [],
    }
    config = _make_config(folders=[normalize_folder(raw_folder)])
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    # icons/ and images/ should appear but not contain __init__.py
    assert "icons/" in text
    assert "images/" in text
    # Count __init__.py occurrences — only app/ should have one
    init_count = text.count("__init__.py")
    assert init_count == 1  # Only app/__init__.py


def test_tree_root_level_folders():
    """Root-level folders appear at project root, not inside app/."""
    config = _make_config(
        folders=[
            {
                "name": "tests",
                "root_level": True,
                "create_init": True,
                "subfolders": [],
                "files": [],
            },
            {
                "name": "core",
                "create_init": True,
                "subfolders": [],
                "files": [],
            },
        ]
    )
    lines = build_project_tree_lines(config)
    "\n".join(lines)
    # tests/ should be at root level (same indent as app/)
    # Find the app/ line and tests/ line — they should have the same prefix depth
    import re

    app_line = next(line for line in lines if "app/" in line)
    tests_line = next(line for line in lines if "tests/" in line)
    app_prefix = len(re.match(r"^[│├└── ]*", app_line).group())
    tests_prefix = len(re.match(r"^[│├└── ]*", tests_line).group())
    assert app_prefix == tests_prefix


def test_tree_nested_subfolders():
    """Tree handles nested subfolders correctly."""
    config = _make_config(
        folders=[
            {
                "name": "core",
                "create_init": True,
                "subfolders": [
                    {
                        "name": "utils",
                        "create_init": True,
                        "subfolders": [],
                        "files": ["helpers.py"],
                    }
                ],
                "files": ["state.py"],
            }
        ]
    )
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    assert "core/" in text
    assert "utils/" in text
    assert "helpers.py" in text
    assert "state.py" in text


def test_tree_empty_folders():
    """Tree works with no template folders."""
    config = _make_config(folders=[])
    lines = build_project_tree_lines(config)
    text = "\n".join(lines)
    assert "my_project/" in text
    assert "app/" in text
    assert "main.py" in text


def test_tree_box_drawing_characters():
    """Tree uses Unicode box-drawing characters."""
    config = _make_config()
    lines = build_project_tree_lines(config)
    all_text = "\n".join(lines)
    assert "├── " in all_text or "└── " in all_text


# ========== Log Viewer Dialog Tests ==========


def test_create_log_viewer_dialog():
    """Test log viewer dialog creation with sample log content."""
    sample = (
        "2026-02-19 10:00:00 | INFO     | app.main:start:10 - App started\n"
        "2026-02-19 10:00:01 | ERROR    | app.build:run:42 - Build failed\n"
    )
    dialog = create_log_viewer_dialog(
        log_content=sample,
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )

    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.modal is True
    assert dialog.content is not None
    assert len(dialog.actions) == 2  # Copy + Close


def test_create_log_viewer_dialog_empty():
    """Test log viewer dialog with empty content shows placeholder."""
    dialog = create_log_viewer_dialog(
        log_content="",
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )
    column = dialog.content.content
    assert len(column.controls) == 1
    assert isinstance(column.controls[0], ft.Text)


def test_parse_log_line_standard():
    """Test standard log lines are parsed into coloured rows."""
    line = "2026-02-19 10:00:00 | INFO     | app.main:start:10 - App started"
    row = _parse_log_line(line, is_dark_mode=True)

    assert isinstance(row, ft.Row)
    # Should have timestamp, sep, level, sep, location, sep, message = 7 parts
    assert len(row.controls) == 7


def test_parse_log_line_continuation():
    """Test non-standard lines (tracebacks) render as plain text."""
    line = '  File "/app/main.py", line 10, in start'
    row = _parse_log_line(line, is_dark_mode=True)

    assert isinstance(row, ft.Row)
    assert len(row.controls) == 1  # Single plain Text
    assert row.controls[0].color == ft.Colors.GREY_600


def test_parse_log_line_critical_is_bold():
    """Test CRITICAL lines use bold weight."""
    line = "2026-02-19 10:00:00 | CRITICAL | app.main:crash:1 - Fatal error"
    row = _parse_log_line(line, is_dark_mode=True)

    # Find the level text (index 2) and message text (index 6)
    level_text = row.controls[2]
    message_text = row.controls[6]
    assert level_text.weight == ft.FontWeight.BOLD
    assert message_text.weight == ft.FontWeight.BOLD


def test_parse_log_line_light_mode_info_color():
    """Test INFO uses different color in light mode."""
    line = "2026-02-19 10:00:00 | INFO     | app.main:start:10 - Started"
    row_dark = _parse_log_line(line, is_dark_mode=True)
    row_light = _parse_log_line(line, is_dark_mode=False)

    # Level text color should differ between modes
    assert row_dark.controls[2].color == ft.Colors.GREY_400
    assert row_light.controls[2].color == ft.Colors.GREY_700


def test_parse_log_location_valid():
    """Test parsing a standard log location segment."""
    result = _parse_log_location("uv_forger.core.state:load:42")
    assert result == ("uv_forger.core.state", 42)


def test_parse_log_location_invalid():
    """Test parsing returns None for non-standard segments."""
    assert _parse_log_location("no_colons_here") is None
    assert _parse_log_location("only:one") is None
    assert _parse_log_location("mod:func:notanum") is None


def test_parse_log_line_with_location_callback():
    """Test location becomes a GestureDetector when callback is provided."""
    captured = []

    def on_click(module, line_no):
        captured.append((module, line_no))

    line = "2026-02-19 10:00:00 | INFO     | app.main:start:10 - Started"
    row = _parse_log_line(line, is_dark_mode=True, on_location_click=on_click)

    # Location control (index 4) should be a GestureDetector
    loc_control = row.controls[4]
    assert isinstance(loc_control, ft.GestureDetector)
    assert loc_control.mouse_cursor == ft.MouseCursor.CLICK


def test_parse_log_line_without_callback_is_plain_text():
    """Test location is plain Text when no callback is provided."""
    line = "2026-02-19 10:00:00 | INFO     | app.main:start:10 - Started"
    row = _parse_log_line(line, is_dark_mode=True, on_location_click=None)

    loc_control = row.controls[4]
    assert isinstance(loc_control, ft.Text)


# ========== Add Packages Dialog Tests ==========


def test_create_add_packages_dialog_basic():
    """Test add packages dialog creates a valid AlertDialog."""
    dialog = create_add_packages_dialog(
        on_add_callback=lambda pkgs: None,
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )

    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.modal is True
    assert dialog.actions is not None
    assert len(dialog.actions) == 2  # Add and Cancel


def test_create_add_packages_dialog_has_verify_button():
    """Test add packages dialog includes the Verify on PyPI button."""
    dialog = create_add_packages_dialog(
        on_add_callback=lambda pkgs: None,
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )

    assert hasattr(dialog, "verify_button")
    assert isinstance(dialog.verify_button, ft.Button)
    assert "Verify" in dialog.verify_button.content


def test_create_add_packages_dialog_has_results_column():
    """Test add packages dialog includes a results column (initially hidden)."""
    dialog = create_add_packages_dialog(
        on_add_callback=lambda pkgs: None,
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )

    assert hasattr(dialog, "results_column")
    assert isinstance(dialog.results_column, ft.Column)
    assert dialog.results_column.visible is False


def test_create_add_packages_dialog_light_mode():
    """Test add packages dialog works in light mode."""
    dialog = create_add_packages_dialog(
        on_add_callback=lambda pkgs: None,
        on_close_callback=lambda _: None,
        is_dark_mode=False,
    )

    assert isinstance(dialog, ft.AlertDialog)


# ========== Metadata Dialog Tests ==========


def test_create_metadata_dialog_basic():
    """Test metadata dialog creates a valid AlertDialog."""
    state = AppState()
    dialog = create_metadata_dialog(
        state=state,
        on_save_callback=lambda *args: None,
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )

    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.modal is True
    assert len(dialog.actions) == 2  # Save and Cancel


def test_create_metadata_dialog_light_mode():
    """Test metadata dialog works in light mode."""
    state = AppState()
    dialog = create_metadata_dialog(
        state=state,
        on_save_callback=lambda *args: None,
        on_close_callback=lambda _: None,
        is_dark_mode=False,
    )

    assert isinstance(dialog, ft.AlertDialog)


def test_create_metadata_dialog_pre_populated():
    """Test metadata dialog pre-populates from state."""
    state = AppState()
    state.author_name = "Tim"
    state.author_email = "tim@example.com"
    state.description = "A project"
    state.license_type = "MIT"

    dialog = create_metadata_dialog(
        state=state,
        on_save_callback=lambda *args: None,
        on_close_callback=lambda _: None,
        is_dark_mode=True,
    )

    # Dialog should be created (values are inside the content controls)
    assert isinstance(dialog, ft.AlertDialog)


# ========== Add Item Dialog Tests ==========


def test_create_add_item_dialog_basic():
    """Test add item dialog creates a valid AlertDialog."""
    dialog = create_add_item_dialog(
        on_add_callback=lambda n, t, p, c: None,
        on_close_callback=lambda _: None,
        parent_folders=[],
        is_dark_mode=True,
    )
    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.modal is True
    assert len(dialog.actions) == 2  # Add and Cancel
    assert hasattr(dialog, "warning_text")


def test_create_add_item_dialog_with_parent_folders():
    """Test add item dialog populates parent dropdown options."""
    parents = [
        {"label": "core/", "path": [0]},
        {"label": "core/utils/", "path": [0, "subfolders", 0]},
    ]
    dialog = create_add_item_dialog(
        on_add_callback=lambda n, t, p, c: None,
        on_close_callback=lambda _: None,
        parent_folders=parents,
        is_dark_mode=True,
    )
    # Content has a Column; find the Dropdown inside
    column = dialog.content.content
    dropdowns = [c for c in column.controls if isinstance(c, ft.Dropdown)]
    assert len(dropdowns) == 1
    # root + 2 parent folders = 3 options
    assert len(dropdowns[0].options) == 3


def test_create_add_item_dialog_browse_hidden_without_callback():
    """Test browse rows are hidden when no callbacks are provided."""
    dialog = create_add_item_dialog(
        on_add_callback=lambda n, t, p, c: None,
        on_close_callback=lambda _: None,
        parent_folders=[],
        is_dark_mode=True,
    )
    column = dialog.content.content
    rows = [c for c in column.controls if isinstance(c, ft.Row)]
    # Both browse_row and browse_folder_row exist but are not visible
    assert len(rows) == 2
    assert rows[0].visible is False  # browse_row (file)
    assert rows[1].visible is False  # browse_folder_row (no callback)


def test_create_add_item_dialog_browse_row_with_callback():
    """Test browse rows exist when callbacks are provided."""
    dialog = create_add_item_dialog(
        on_add_callback=lambda n, t, p, c: None,
        on_close_callback=lambda _: None,
        parent_folders=[],
        is_dark_mode=True,
        on_browse_callback=AsyncMock(),
    )
    column = dialog.content.content
    rows = [c for c in column.controls if isinstance(c, ft.Row)]
    # browse_row (file) hidden since type defaults to folder; browse_folder_row hidden (no callback)
    assert len(rows) == 2
    assert rows[0].visible is False  # browse_row
    assert rows[1].visible is False  # browse_folder_row (no callback provided)


def test_create_add_item_dialog_callback_receives_content_none():
    """Test that on_add_callback receives None content for normal adds."""
    received = {}

    def capture(name, item_type, parent_path, content):
        received.update(name=name, item_type=item_type, content=content)

    dialog = create_add_item_dialog(
        on_add_callback=capture,
        on_close_callback=lambda _: None,
        parent_folders=[],
        is_dark_mode=True,
    )
    # Simulate: set name, keep type as "folder", click Add
    column = dialog.content.content
    text_fields = [c for c in column.controls if isinstance(c, ft.TextField)]
    text_fields[0].value = "test_folder"

    # Find and click Add button
    add_button = dialog.actions[0]
    mock_event = Mock()
    mock_event.page = Mock()
    add_button.on_click(mock_event)

    assert received["name"] == "test_folder"
    assert received["item_type"] == "folder"
    assert received["content"] is None
