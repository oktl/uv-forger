#!/usr/bin/env python3
"""Pytest tests for validator.py functions"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

from uv_forger.core.validator import (
    _MAX_NAME_LENGTH,
    validate_folder_name,
    validate_path,
    validate_project_name,
)


@pytest.mark.parametrize(
    "name,expected_valid,description",
    [
        ("my_project", True, "Valid name with underscore"),
        ("my-project", True, "Valid name with hyphen"),
        ("MyProject", True, "Valid name with capitals"),
        ("project123", True, "Valid name with numbers"),
        ("_private", True, "Valid name starting with underscore"),
        ("", False, "Empty name"),
        ("123project", False, "Starts with number"),
        ("-project", False, "Starts with hyphen"),
        ("my project", False, "Contains space"),
        ("my@project", False, "Contains special char"),
        ("class", False, "Python keyword"),
        ("for", False, "Python keyword"),
        ("a" * (_MAX_NAME_LENGTH + 1), False, "Exceeds max length"),
    ],
)
def test_validate_project_name(name, expected_valid, description):
    """Test project name validation"""
    is_valid, error_msg = validate_project_name(name)
    assert is_valid == expected_valid, f"{description}: {error_msg}"


def test_validate_project_name_at_max_length():
    """Test that a name exactly at the max length is accepted."""
    name = "a" * _MAX_NAME_LENGTH
    is_valid, _ = validate_project_name(name)
    assert is_valid


@pytest.mark.parametrize(
    "name,expected_valid,description",
    [
        ("my_folder", True, "Valid folder with underscore"),
        ("my-folder", True, "Valid folder with hyphen"),
        ("MyFolder", True, "Valid folder with capitals"),
        ("folder123", True, "Valid folder with numbers"),
        ("123folder", True, "Valid folder starting with number"),
        ("", False, "Empty name"),
        ("my folder", False, "Contains space"),
        ("my@folder", False, "Contains special char"),
        ("a" * (_MAX_NAME_LENGTH + 1), False, "Exceeds max length"),
    ],
)
def test_validate_folder_name(name, expected_valid, description):
    """Test folder name validation"""
    is_valid, error_msg = validate_folder_name(name)
    assert is_valid == expected_valid, f"{description}: {error_msg}"


def test_validate_path_new_folder():
    """Test validation of a new path with a writable parent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "new_folder"
        is_valid, error_msg = validate_path(test_path)
        assert is_valid, f"Valid new path should pass: {error_msg}"
        # Verify the directory was NOT created (validation is read-only)
        assert not test_path.exists(), "validate_path should not create directories"


def test_validate_path_existing_directory():
    """Test validation of an existing directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir)
        is_valid, error_msg = validate_path(test_path)
        assert is_valid, f"Existing directory should be valid: {error_msg}"


def test_validate_path_file_not_directory():
    """Test that a file path (not directory) is rejected"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_file = Path(tmp.name)
    try:
        is_valid, error_msg = validate_path(tmp_file)
        assert not is_valid, "File path should be rejected"
        assert "not a" in error_msg.lower() and "directory" in error_msg.lower()
    finally:
        tmp_file.unlink()


def test_validate_path_nonexistent_nested_path():
    """Test validation of a deeply nested path where parent exists and is writable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "a" / "b" / "c"
        is_valid, error_msg = validate_path(test_path)
        assert is_valid, f"Nested path under writable parent should pass: {error_msg}"


@pytest.mark.skipif(sys.platform == "win32", reason="chmod not enforced on Windows")
def test_validate_path_unwritable_parent():
    """Test that a path under a read-only directory is rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        readonly_dir = Path(tmpdir) / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)
        try:
            test_path = readonly_dir / "new_project"
            is_valid, error_msg = validate_path(test_path)
            assert not is_valid, "Path under read-only dir should be rejected"
            assert (
                "not writable" in error_msg.lower()
                or "permission denied" in error_msg.lower()
            )
        finally:
            os.chmod(readonly_dir, 0o755)


@pytest.mark.skipif(sys.platform == "win32", reason="chmod not enforced on Windows")
def test_validate_path_existing_unwritable_directory():
    """Test that an existing read-only directory is rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        readonly_dir = Path(tmpdir) / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)
        try:
            is_valid, error_msg = validate_path(readonly_dir)
            assert not is_valid, "Read-only directory should be rejected"
            assert "not writable" in error_msg.lower()
        finally:
            os.chmod(readonly_dir, 0o755)
