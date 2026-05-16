"""Test suite for project_builder.py"""

import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

from uv_forger.core.models import ProjectConfig
from uv_forger.handlers.project_builder import (
    _collect_packages_to_install,
    build_project,
    remove_partial_project,
)


class TestRemovePartialProject:
    """Tests for the remove_partial_project rollback function"""

    def test_removes_project_directory(self):
        """Test that the project directory is removed on cleanup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            assert project_path.exists()

            remove_partial_project(project_path)

            assert not project_path.exists()

    def test_removes_bare_repo_when_provided(self):
        """Test that the bare hub repo is removed alongside the project dir"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            bare_repo = Path(tmpdir) / "myproject.git"
            bare_repo.mkdir()

            remove_partial_project(project_path, bare_repo)

            assert not project_path.exists()
            assert not bare_repo.exists()

    def test_bare_repo_none_does_not_raise(self):
        """Test that passing None for bare_repo_path is safe (git disabled)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()

            remove_partial_project(project_path, None)

            assert not project_path.exists()

    def test_handles_nonexistent_project_path(self):
        """Test that cleanup is safe when the project dir was never created"""
        nonexistent = Path("/tmp/nonexistent_create_project_test_xyz")
        remove_partial_project(nonexistent)  # Should not raise

    def test_handles_nonexistent_bare_repo(self):
        """Test that cleanup is safe when bare repo was never created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            nonexistent_bare = Path(tmpdir) / "nonexistent.git"

            remove_partial_project(project_path, nonexistent_bare)  # Should not raise

            assert not project_path.exists()

    def test_removes_nested_project_contents(self):
        """Test that cleanup recursively removes nested files and directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            nested = project_path / "app" / "core"
            nested.mkdir(parents=True)
            (nested / "state.py").write_text("# state")

            remove_partial_project(project_path)

            assert not project_path.exists()


def _make_config(tmpdir, **kwargs) -> ProjectConfig:
    """Helper to build a minimal ProjectConfig rooted in a temp directory."""
    defaults = {
        "project_name": "my_project",
        "project_path": Path(tmpdir),
        "python_version": "3.14",
        "git_enabled": False,
        "ui_project_enabled": False,
        "framework": "",
        "other_project_enabled": False,
        "project_type": None,
        "packages": [],
    }
    defaults.update(kwargs)
    return ProjectConfig(**defaults)


class TestCollectPackagesToInstall:
    """Tests for _collect_packages_to_install package resolution logic."""

    def test_explicit_packages_returned_directly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, packages=["httpx", "rich"])
            runtime, dev = _collect_packages_to_install(config)
            assert runtime == ["httpx", "rich"]
            assert dev == []

    def test_explicit_packages_skip_framework_lookup(self):
        """Explicit list wins even when framework is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(
                tmpdir,
                packages=["mylib"],
                ui_project_enabled=True,
                framework="flet",
            )
            runtime, dev = _collect_packages_to_install(config)
            assert runtime == ["mylib"]
            assert dev == []

    def test_framework_package_added_when_ui_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, ui_project_enabled=True, framework="flet")
            runtime, dev = _collect_packages_to_install(config)
            assert "flet" in runtime

    def test_builtin_framework_returns_no_package(self):
        """tkinter is built-in; FRAMEWORK_PACKAGE_MAP maps it to None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(
                tmpdir,
                ui_project_enabled=True,
                framework="tkinter (built-in)",
            )
            runtime, dev = _collect_packages_to_install(config)
            assert runtime == []
            assert dev == []

    def test_project_type_packages_added_when_other_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(
                tmpdir,
                other_project_enabled=True,
                project_type="fastapi",
            )
            runtime, dev = _collect_packages_to_install(config)
            assert "fastapi" in runtime
            assert "uvicorn" in runtime

    def test_both_flags_combine_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(
                tmpdir,
                ui_project_enabled=True,
                framework="flet",
                other_project_enabled=True,
                project_type="cli_click",
            )
            runtime, dev = _collect_packages_to_install(config)
            assert "flet" in runtime
            assert "click" in runtime

    def test_no_flags_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir)
            runtime, dev = _collect_packages_to_install(config)
            assert runtime == []
            assert dev == []

    def test_unknown_project_type_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(
                tmpdir,
                other_project_enabled=True,
                project_type="nonexistent_type",
            )
            runtime, dev = _collect_packages_to_install(config)
            assert runtime == []
            assert dev == []

    def test_dev_packages_split_from_runtime(self):
        """Dev packages are separated from runtime when explicit list provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(
                tmpdir,
                packages=["httpx", "pytest", "rich"],
                dev_packages=["pytest"],
            )
            runtime, dev = _collect_packages_to_install(config)
            assert runtime == ["httpx", "rich"]
            assert dev == ["pytest"]


class TestBuildProjectErrors:
    """Tests for build_project error handling and validation."""

    def test_invalid_project_name_returns_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, project_name="")
            result = build_project(config)
            assert not result.success
            assert result.message

    def test_invalid_name_with_spaces_returns_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, project_name="my project")
            result = build_project(config)
            assert not result.success

    def test_called_process_error_returns_failure_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, project_name="my_proj")
            cmd_error = CalledProcessError(1, ["uv", "init"], stderr="some error")

            with patch(
                "uv_forger.handlers.project_builder._create_project_scaffold",
                side_effect=cmd_error,
            ):
                result = build_project(config)

            assert not result.success
            assert "Command failed" in result.message
            # Project directory should be cleaned up
            assert not (Path(tmpdir) / "my_proj").exists()

    def test_os_error_returns_failure_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, project_name="my_proj")

            with patch(
                "uv_forger.handlers.project_builder._create_project_scaffold",
                side_effect=OSError("disk full"),
            ):
                result = build_project(config)

            assert not result.success
            assert "Could not create project files" in result.message

    def test_generic_exception_returns_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, project_name="my_proj")

            with patch(
                "uv_forger.handlers.project_builder._create_project_scaffold",
                side_effect=RuntimeError("unexpected"),
            ):
                result = build_project(config)

            assert not result.success

    def test_missing_base_directory_creates_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = Path(tmpdir) / "a" / "b" / "c"
            config = _make_config(deep_path, project_name="my_proj")

            with (
                patch(
                    "uv_forger.handlers.project_builder._create_project_scaffold"
                ) as mock_scaffold,
                patch("uv_forger.handlers.project_builder._install_dependencies"),
                patch("uv_forger.handlers.project_builder.finalize_git_setup"),
            ):
                mock_scaffold.return_value = None
                build_project(config)

            assert deep_path.exists()

    def test_base_dir_creation_failure_returns_error(self):
        """OSError while creating missing base dir returns clean error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(Path(tmpdir) / "missing_base", project_name="my_proj")
            with patch("pathlib.Path.mkdir", side_effect=OSError("permission denied")):
                result = build_project(config)

            assert not result.success
            assert "Could not create base directory" in result.message

    def test_success_returns_success_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(tmpdir, project_name="my_proj")

            with (
                patch("uv_forger.handlers.project_builder._create_project_scaffold"),
                patch("uv_forger.handlers.project_builder._install_dependencies"),
                patch("uv_forger.handlers.project_builder.finalize_git_setup"),
            ):
                result = build_project(config)

            assert result.success
            assert "my_proj" in result.message
