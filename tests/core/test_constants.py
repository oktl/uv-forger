#!/usr/bin/env python3
"""Pytest tests for constants.py — structural consistency checks."""

from uv_forger.core.constants import (
    BOILERPLATE_DIR,
    DEFAULT_FRAMEWORK,
    DEFAULT_PYTHON_VERSION,
    FRAMEWORK_ENTRY_POINT_MAP,
    FRAMEWORK_PACKAGE_MAP,
    PROJECT_TYPE_ENTRY_POINT_MAP,
    PROJECT_TYPE_PACKAGE_MAP,
    PROJECT_TYPE_TEMPLATES_DIR,
    PYTHON_VERSIONS,
    TEMPLATES_DIR,
    UI_FRAMEWORKS,
    UI_TEMPLATES_DIR,
)


def test_default_python_version_in_versions():
    """DEFAULT_PYTHON_VERSION must be in PYTHON_VERSIONS list."""
    assert DEFAULT_PYTHON_VERSION in PYTHON_VERSIONS


def test_default_framework_in_frameworks():
    """DEFAULT_FRAMEWORK must be in UI_FRAMEWORKS list."""
    assert DEFAULT_FRAMEWORK in UI_FRAMEWORKS


def test_no_duplicate_frameworks():
    """UI_FRAMEWORKS should not contain duplicates."""
    assert len(UI_FRAMEWORKS) == len(set(UI_FRAMEWORKS))


def test_no_duplicate_python_versions():
    """PYTHON_VERSIONS should not contain duplicates."""
    assert len(PYTHON_VERSIONS) == len(set(PYTHON_VERSIONS))


def test_framework_package_map_matches_ui_frameworks():
    """Every UI framework must have an entry in FRAMEWORK_PACKAGE_MAP."""
    assert set(UI_FRAMEWORKS) == set(FRAMEWORK_PACKAGE_MAP.keys())


def test_framework_entry_point_map_matches_ui_frameworks():
    """Every UI framework must have an entry in FRAMEWORK_ENTRY_POINT_MAP."""
    assert set(UI_FRAMEWORKS) == set(FRAMEWORK_ENTRY_POINT_MAP.keys())


def test_project_type_maps_are_consistent():
    """PROJECT_TYPE_PACKAGE_MAP and PROJECT_TYPE_ENTRY_POINT_MAP must have the same keys."""
    assert set(PROJECT_TYPE_PACKAGE_MAP.keys()) == set(
        PROJECT_TYPE_ENTRY_POINT_MAP.keys()
    )


def test_templates_directory_exists():
    """Templates directory must exist on disk."""
    assert TEMPLATES_DIR.is_dir()


def test_ui_templates_directory_exists():
    """UI templates directory must exist on disk."""
    assert UI_TEMPLATES_DIR.is_dir()


def test_project_type_templates_directory_exists():
    """Project type templates directory must exist on disk."""
    assert PROJECT_TYPE_TEMPLATES_DIR.is_dir()


def test_boilerplate_directory_exists():
    """Boilerplate directory must exist on disk."""
    assert BOILERPLATE_DIR.is_dir()
