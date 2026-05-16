#!/usr/bin/env python3
"""Pytest tests for state.py - AppState dataclass"""

import pytest

from uv_forger.core.constants import DEFAULT_PROJECT_ROOT, DEFAULT_PYTHON_VERSION
from uv_forger.core.state import AppState


def test_appstate_initialization():
    """Test AppState initializes with correct defaults"""
    state = AppState()

    assert state.project_path == str(DEFAULT_PROJECT_ROOT)
    assert state.project_name == ""
    assert state.python_version == DEFAULT_PYTHON_VERSION
    assert state.git_enabled
    assert not state.ui_project_enabled
    assert state.framework is None
    assert not state.other_project_enabled
    assert state.project_type is None
    assert state.folders == []
    assert state.is_dark_mode
    assert state.path_valid
    assert not state.name_valid  # Empty name is invalid


def test_appstate_custom_initialization():
    """Test AppState with custom values"""
    state = AppState(
        project_path="/custom/path",
        project_name="my_project",
        python_version="3.12",
        git_enabled=True,
        ui_project_enabled=True,
        framework="flet",
        other_project_enabled=True,
        project_type="django",
        folders=["core", "ui", "utils"],
        is_dark_mode=False,
        path_valid=False,
        name_valid=True,
    )

    assert state.project_path == "/custom/path"
    assert state.project_name == "my_project"
    assert state.python_version == "3.12"
    assert state.git_enabled
    assert state.ui_project_enabled
    assert state.framework == "flet"
    assert state.other_project_enabled
    assert state.project_type == "django"
    assert state.folders == ["core", "ui", "utils"]
    assert not state.is_dark_mode
    assert not state.path_valid
    assert state.name_valid


def test_appstate_reset():
    """Test AppState.reset() method resets all fields except is_dark_mode"""
    # Create state with custom values
    state = AppState(
        project_path="/custom/path",
        project_name="my_project",
        python_version="3.12",
        git_enabled=True,
        ui_project_enabled=True,
        framework="flet",
        other_project_enabled=True,
        project_type="django",
        folders=["core", "ui", "utils"],
        is_dark_mode=False,  # Set to False to test it's preserved
        path_valid=False,
        name_valid=True,
    )

    # Reset state
    state.reset()

    # Test reset values (all should be back to defaults except is_dark_mode)
    assert state.project_path == str(DEFAULT_PROJECT_ROOT)
    assert state.project_name == ""
    assert state.python_version == DEFAULT_PYTHON_VERSION
    assert state.git_enabled
    assert not state.ui_project_enabled
    assert state.framework is None
    assert not state.other_project_enabled
    assert state.project_type is None
    assert state.folders == []
    assert not state.is_dark_mode  # PRESERVED (was False, still False)
    assert state.path_valid
    assert not state.name_valid


def test_appstate_reset_preserves_dark_mode_true():
    """Test that reset() preserves is_dark_mode=True"""
    state = AppState(is_dark_mode=True, project_name="test")
    state.reset()
    assert state.is_dark_mode


def test_appstate_reset_preserves_dark_mode_false():
    """Test that reset() preserves is_dark_mode=False"""
    state = AppState(is_dark_mode=False, project_name="test")
    state.reset()
    assert not state.is_dark_mode


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_path", "/new/path"),
        ("project_name", "new_name"),
        ("python_version", "3.11"),
        ("git_enabled", True),
        ("ui_project_enabled", True),
        ("framework", "pyqt6"),
        ("other_project_enabled", True),
        ("project_type", "fastapi"),
        ("is_dark_mode", False),
        ("path_valid", False),
        ("name_valid", True),
    ],
)
def test_appstate_field_mutability(field, value):
    """Test that AppState fields are mutable"""
    state = AppState()
    setattr(state, field, value)
    assert getattr(state, field) == value


def test_appstate_folders_mutability():
    """Test that folders list is mutable"""
    state = AppState()
    state.folders = ["new", "folders"]
    assert state.folders == ["new", "folders"]


def test_appstate_folders_independence():
    """Test that folders list is independent across instances"""
    state1 = AppState()
    state2 = AppState()

    # Modify folders in state1
    state1.folders.append("test_folder")

    # Verify state2 folders is not affected
    assert "test_folder" not in state2.folders
    # Verify state1 has the folder
    assert "test_folder" in state1.folders


# ========== Project Type Tests ==========


def test_appstate_project_type_defaults():
    """Test project type fields initialize with correct defaults"""
    state = AppState()
    assert not state.other_project_enabled
    assert state.project_type is None


def test_appstate_other_project_enabled_mutability():
    """Test other_project_enabled field is mutable"""
    state = AppState()
    assert not state.other_project_enabled

    state.other_project_enabled = True
    assert state.other_project_enabled

    state.other_project_enabled = False
    assert not state.other_project_enabled


def test_appstate_project_type_mutability():
    """Test project_type field is mutable"""
    state = AppState()
    assert state.project_type is None

    state.project_type = "django"
    assert state.project_type == "django"

    state.project_type = "fastapi"
    assert state.project_type == "fastapi"

    state.project_type = None
    assert state.project_type is None


@pytest.mark.parametrize(
    "project_type",
    [
        "django",
        "fastapi",
        "flask",
        "data_analysis",
        "cli_typer",
        "scraping",
        "ml_sklearn",
        "api_graphql",
    ],
)
def test_appstate_various_project_types(project_type):
    """Test AppState can store various project type values"""
    state = AppState(project_type=project_type)
    assert state.project_type == project_type


def test_appstate_mutual_exclusion_concept():
    """Test that both checkboxes can be tracked independently in state"""
    # Note: Mutual exclusion is enforced in event handlers, not state
    state = AppState()

    # Can set UI project
    state.ui_project_enabled = True
    state.framework = "flet"
    assert state.ui_project_enabled
    assert state.framework == "flet"

    # State allows both to be set (handlers enforce mutual exclusion)
    state.other_project_enabled = True
    state.project_type = "django"
    assert state.other_project_enabled
    assert state.project_type == "django"


def test_appstate_reset_clears_project_type():
    """Test reset() clears project type fields"""
    state = AppState(other_project_enabled=True, project_type="fastapi")

    assert state.other_project_enabled
    assert state.project_type == "fastapi"

    state.reset()

    assert not state.other_project_enabled
    assert state.project_type is None
