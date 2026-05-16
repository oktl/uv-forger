#!/usr/bin/env python3
"""Pytest tests for models.py"""

from pathlib import Path

from uv_forger.core.models import (
    BuildResult,
    BuildSummaryConfig,
    FolderSpec,
    ProjectConfig,
)

# FolderSpec Tests


def test_folder_spec_basic_creation():
    """Test basic FolderSpec creation with defaults"""
    folder = FolderSpec(name="test_folder")
    assert folder.name == "test_folder"
    assert folder.create_init
    assert not folder.root_level


def test_folder_spec_all_parameters():
    """Test FolderSpec with all parameters"""
    folder = FolderSpec(
        name="custom",
        create_init=False,
        root_level=True,
        subfolders=["sub1", "sub2"],
        files=["file1.py", "file2.py"],
    )
    assert folder.name == "custom"
    assert not folder.create_init
    assert folder.root_level
    assert len(folder.subfolders) == 2
    assert len(folder.files) == 2


def test_folder_spec_to_dict():
    """Test FolderSpec.to_dict()"""
    folder = FolderSpec(
        name="handlers", create_init=False, root_level=True, files=["git_handler.py"]
    )
    result = folder.to_dict()
    assert isinstance(result, dict)
    assert result["name"] == "handlers"
    assert not result["create_init"]
    assert result["root_level"]
    assert len(result["files"]) == 1


def test_folder_spec_to_dict_omits_defaults():
    """Test that to_dict() omits fields with default values"""
    folder = FolderSpec(name="minimal")
    result = folder.to_dict()
    assert result == {"name": "minimal"}
    assert "create_init" not in result  # True is default, omitted
    assert "root_level" not in result  # False is default, omitted
    assert "subfolders" not in result
    assert "files" not in result


def test_folder_spec_to_dict_nested():
    """Test FolderSpec.to_dict() with nested subfolders"""
    nested = FolderSpec(name="nested", create_init=True)
    folder = FolderSpec(name="parent", subfolders=[nested, "simple_string"])
    result = folder.to_dict()
    assert isinstance(result["subfolders"], list)
    assert isinstance(result["subfolders"][0], dict)
    assert result["subfolders"][0]["name"] == "nested"
    assert result["subfolders"][1] == "simple_string"


# ProjectConfig Tests


def test_project_config_basic_creation():
    """Test basic ProjectConfig creation"""
    config = ProjectConfig(
        project_name="my_project",
        project_path=Path("/tmp"),
        python_version="3.14",
        git_enabled=True,
        ui_project_enabled=False,
        framework="",
    )
    assert config.project_name == "my_project"
    assert config.project_path == Path("/tmp")
    assert config.python_version == "3.14"
    assert config.git_enabled


def test_project_config_full_path():
    """Test ProjectConfig.full_path property"""
    config = ProjectConfig(
        project_name="test_app",
        project_path=Path("/home/user/projects"),
        python_version="3.14",
        git_enabled=True,
        ui_project_enabled=True,
        framework="flet",
    )
    full_path = config.full_path
    expected = Path("/home/user/projects/test_app")
    assert full_path == expected


def test_project_config_effective_framework_when_enabled():
    """Test effective_framework returns framework when UI is enabled"""
    config = ProjectConfig(
        project_name="test",
        project_path=Path("/tmp"),
        python_version="3.14",
        ui_project_enabled=True,
        framework="flet",
    )
    assert config.effective_framework == "flet"


def test_project_config_effective_framework_when_disabled():
    """Test effective_framework returns None when UI is disabled"""
    config = ProjectConfig(
        project_name="test",
        project_path=Path("/tmp"),
        python_version="3.14",
        ui_project_enabled=False,
        framework="flet",
    )
    assert config.effective_framework is None


def test_project_config_effective_project_type_when_enabled():
    """Test effective_project_type returns type when enabled"""
    config = ProjectConfig(
        project_name="test",
        project_path=Path("/tmp"),
        python_version="3.14",
        other_project_enabled=True,
        project_type="django",
    )
    assert config.effective_project_type == "django"


def test_project_config_effective_project_type_when_disabled():
    """Test effective_project_type returns None when disabled"""
    config = ProjectConfig(
        project_name="test",
        project_path=Path("/tmp"),
        python_version="3.14",
        other_project_enabled=False,
        project_type="django",
    )
    assert config.effective_project_type is None


def test_project_config_mixed_folder_types():
    """Test ProjectConfig with mixed folder types"""
    folder_spec = FolderSpec(name="models")
    config = ProjectConfig(
        project_name="test",
        project_path=Path("/tmp"),
        python_version="3.14",
        git_enabled=False,
        ui_project_enabled=False,
        framework="",
        folders=["simple", {"name": "dict_folder"}, folder_spec],
    )
    assert len(config.folders) == 3
    assert isinstance(config.folders[0], str)
    assert isinstance(config.folders[1], dict)
    assert isinstance(config.folders[2], FolderSpec)


# BuildResult Tests


def test_build_result_success():
    """Test BuildResult success"""
    result = BuildResult(success=True, message="Project created successfully")
    assert result.success
    assert result.message
    assert result.error is None


def test_build_result_failure_with_exception():
    """Test BuildResult failure with exception"""
    test_exception = ValueError("Test error")
    result = BuildResult(success=False, message="Build failed", error=test_exception)
    assert not result.success
    assert result.message == "Build failed"
    assert isinstance(result.error, ValueError)


def test_build_result_failure_without_exception():
    """Test BuildResult failure without exception"""
    result = BuildResult(success=False, message="Validation failed")
    assert not result.success
    assert result.error is None


# BuildSummaryConfig Tests


def test_build_summary_config_creation():
    """Test BuildSummaryConfig basic creation"""
    config = BuildSummaryConfig(
        project_name="my_app",
        project_path="/home/user/projects",
        python_version="3.14",
        git_enabled=True,
        ui_project_enabled=True,
        framework="flet",
        other_project_enabled=False,
        project_type=None,
        starter_files=True,
        folder_count=5,
        file_count=10,
    )
    assert config.project_name == "my_app"
    assert config.framework == "flet"
    assert config.folder_count == 5
    assert config.packages == []
    assert config.folders == []


def test_build_summary_config_from_project_config():
    """Test BuildSummaryConfig.from_project_config factory method"""
    project_config = ProjectConfig(
        project_name="my_app",
        project_path=Path("/home/user/projects"),
        python_version="3.14",
        git_enabled=True,
        ui_project_enabled=True,
        framework="flet",
        other_project_enabled=False,
        project_type="django",
        include_starter_files=True,
        packages=["flet", "httpx"],
    )
    summary = BuildSummaryConfig.from_project_config(
        config=project_config,
        folder_count=5,
        file_count=10,
        folders=["core", "utils"],
    )
    assert summary.project_name == "my_app"
    assert summary.project_path == str(Path("/home/user/projects"))
    assert summary.python_version == "3.14"
    assert summary.git_enabled is True
    assert summary.framework == "flet"  # effective_framework since ui enabled
    assert summary.project_type is None  # effective_project_type since other disabled
    assert summary.starter_files is True
    assert summary.folder_count == 5
    assert summary.file_count == 10
    assert summary.packages == ["flet", "httpx"]
    assert summary.folders == ["core", "utils"]
