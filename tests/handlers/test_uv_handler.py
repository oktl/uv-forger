"""Test suite for uv_handler.py"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uv_forger.handlers.uv_handler import (
    _resolve_entry_point,
    configure_pyproject,
    get_uv_path,
    run_uv_init,
    setup_virtual_env,
)


@pytest.fixture
def check_uv_available():
    """Check if uv is available in the system"""
    try:
        subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class TestGetUvPath:
    """Tests for get_uv_path function"""

    def test_find_uv_in_path(self):
        """Test find uv in PATH"""
        try:
            uv_path = get_uv_path()
            assert uv_path is not None
            assert Path(uv_path).exists()
        except FileNotFoundError:
            # This is expected if uv is not installed
            pytest.skip("UV not found (expected if not installed)")

    def test_raises_error_when_not_found(self):
        """Test FileNotFoundError when uv not found"""
        with patch('shutil.which', return_value=None):
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(FileNotFoundError) as exc_info:
                    get_uv_path()
                assert "Could not find 'uv' executable" in str(exc_info.value)

    def test_windows_path_handling(self):
        """Test platform-specific path handling"""
        with patch('shutil.which', return_value=None):
            with patch('platform.system', return_value='Windows'):
                with patch('pathlib.Path.exists', return_value=False):
                    with pytest.raises(FileNotFoundError):
                        get_uv_path()


class TestConfigurePyproject:
    """Tests for configure_pyproject function"""

    def test_append_configuration(self):
        """Test append configuration to pyproject.toml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            pyproject_file = project_path / "pyproject.toml"

            # Create initial pyproject.toml
            initial_content = "[project]\nname = \"test-project\"\n"
            pyproject_file.write_text(initial_content)

            # Configure it
            configure_pyproject(project_path, "test_project")

            # Read the result
            final_content = pyproject_file.read_text()

            # Check if configuration was appended
            assert initial_content in final_content
            assert "[tool.hatch.build.targets.wheel]" in final_content
            assert 'packages = ["app"]' in final_content
            assert "[project.scripts]" in final_content
            assert 'test_project = "app.main:main"' in final_content

    def test_format_of_appended_content(self):
        """Test verify format of appended content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            pyproject_file = project_path / "pyproject.toml"
            pyproject_file.write_text("")

            configure_pyproject(project_path, "my_app")

            content = pyproject_file.read_text()
            # Check that it starts with a newline (for separation)
            assert content.startswith('\n')

    def test_different_project_names(self):
        """Test different project names"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            pyproject_file = project_path / "pyproject.toml"
            pyproject_file.write_text("")

            configure_pyproject(project_path, "my-cool-app")

            content = pyproject_file.read_text()
            assert 'my-cool-app = "app.main:main"' in content


class TestUvCommandsWithMocks:
    """Tests for uv command functions with mocks"""

    def test_run_uv_init_command_structure(self):
        """Test run_uv_init command structure"""
        with patch('uv_forger.handlers.uv_handler.get_uv_path', return_value='/usr/bin/uv'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with tempfile.TemporaryDirectory() as tmpdir:
                    project_path = Path(tmpdir)
                    run_uv_init(project_path, "3.14")

                    # Verify subprocess.run was called with correct arguments
                    call_args = mock_run.call_args
                    cmd = call_args[0][0]

                    assert cmd == ['/usr/bin/uv', 'init', '--python', '3.14', '.']
                    assert call_args[1]['cwd'] == project_path
                    assert call_args[1]['check'] == True

    def test_setup_virtual_env_command_structure(self):
        """Test setup_virtual_env command structure"""
        with patch('uv_forger.handlers.uv_handler.get_uv_path', return_value='/usr/bin/uv'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with tempfile.TemporaryDirectory() as tmpdir:
                    project_path = Path(tmpdir)
                    setup_virtual_env(project_path, "3.14")

                    # Should be called twice: venv and sync
                    assert mock_run.call_count == 2

                    # Check first call (venv)
                    first_call = mock_run.call_args_list[0][0][0]
                    # Check second call (sync)
                    second_call = mock_run.call_args_list[1][0][0]

                    assert first_call == ['/usr/bin/uv', 'venv', '--python', '3.14']
                    assert second_call == ['/usr/bin/uv', 'sync']

class TestResolveEntryPoint:
    """Tests for _resolve_entry_point helper"""

    def test_default_no_framework_no_project_type(self):
        """Default entry point when nothing is selected"""
        assert _resolve_entry_point() == "app.main:main"

    def test_flet_framework(self):
        """Flet framework uses app.main:run"""
        assert _resolve_entry_point(framework="flet") == "app.main:run"

    def test_gui_frameworks_use_run(self):
        """All GUI frameworks use app.main:run"""
        for fw in ["PyQt6", "PySide6", "tkinter (built-in)", "customtkinter",
                    "kivy", "pygame", "nicegui"]:
            assert _resolve_entry_point(framework=fw) == "app.main:run", f"{fw} failed"

    def test_streamlit_no_entry_point(self):
        """Streamlit has its own runner — no entry point"""
        assert _resolve_entry_point(framework="streamlit") is None

    def test_gradio_no_entry_point(self):
        """Gradio has its own runner — no entry point"""
        assert _resolve_entry_point(framework="gradio") is None

    def test_django_no_entry_point(self):
        """Django has its own runner — no entry point"""
        assert _resolve_entry_point(project_type="django") is None

    def test_fastapi_no_entry_point(self):
        """FastAPI has its own runner — no entry point"""
        assert _resolve_entry_point(project_type="fastapi") is None

    def test_flask_no_entry_point(self):
        """Flask has its own runner — no entry point"""
        assert _resolve_entry_point(project_type="flask") is None

    def test_cli_click_entry_point(self):
        """Click CLI uses app.main:cli"""
        assert _resolve_entry_point(project_type="cli_click") == "app.main:cli"

    def test_cli_typer_entry_point(self):
        """Typer CLI uses app.main:app"""
        assert _resolve_entry_point(project_type="cli_typer") == "app.main:app"

    def test_cli_rich_entry_point(self):
        """Rich CLI uses app.main:main"""
        assert _resolve_entry_point(project_type="cli_rich") == "app.main:main"

    def test_framework_takes_priority_over_project_type(self):
        """Framework entry point takes priority over project type"""
        result = _resolve_entry_point(framework="flet", project_type="cli_click")
        assert result == "app.main:run"

    def test_unknown_framework_uses_default(self):
        """Unknown framework falls back to default"""
        assert _resolve_entry_point(framework="unknown_fw") == "app.main:main"

    def test_unknown_project_type_uses_default(self):
        """Unknown project type falls back to default"""
        assert _resolve_entry_point(project_type="unknown_pt") == "app.main:main"


class TestConfigurePyprojectWithContext:
    """Tests for configure_pyproject with framework/project_type context"""

    def test_flet_project_has_run_entry_point(self):
        """Flet project should have app.main:run"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp", framework="flet")

            content = (project_path / "pyproject.toml").read_text()
            assert '[project.scripts]' in content
            assert 'myapp = "app.main:run"' in content

    def test_django_project_has_no_scripts(self):
        """Django project should NOT have [project.scripts]"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp", project_type="django")

            content = (project_path / "pyproject.toml").read_text()
            assert '[tool.hatch.build.targets.wheel]' in content
            assert '[project.scripts]' not in content

    def test_streamlit_project_has_no_scripts(self):
        """Streamlit project should NOT have [project.scripts]"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp", framework="streamlit")

            content = (project_path / "pyproject.toml").read_text()
            assert '[tool.hatch.build.targets.wheel]' in content
            assert '[project.scripts]' not in content

    def test_cli_click_entry_point(self):
        """Click CLI project should have app.main:cli"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp", project_type="cli_click")

            content = (project_path / "pyproject.toml").read_text()
            assert 'myapp = "app.main:cli"' in content

    def test_cli_typer_entry_point(self):
        """Typer CLI project should have app.main:app"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp", project_type="cli_typer")

            content = (project_path / "pyproject.toml").read_text()
            assert 'myapp = "app.main:app"' in content

    def test_hatch_section_always_written(self):
        """Hatch build config should always be present"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp", project_type="django")

            content = (project_path / "pyproject.toml").read_text()
            assert '[tool.hatch.build.targets.wheel]' in content
            assert 'packages = ["app"]' in content

    def test_default_bare_project(self):
        """Bare project with no framework/type should use app.main:main"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(project_path, "myapp")

            content = (project_path / "pyproject.toml").read_text()
            assert 'myapp = "app.main:main"' in content

    def test_framework_priority_over_project_type(self):
        """Framework entry point takes priority over project type"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text("")

            configure_pyproject(
                project_path, "myapp",
                framework="flet", project_type="cli_click",
            )

            content = (project_path / "pyproject.toml").read_text()
            assert 'myapp = "app.main:run"' in content


class TestConfigurePyprojectMetadata:
    """Tests for configure_pyproject with metadata fields."""

    @staticmethod
    def _uv_pyproject():
        """Return a minimal UV-generated pyproject.toml."""
        return (
            '[project]\n'
            'name = "myapp"\n'
            'version = "0.1.0"\n'
            'description = ""\n'
            'readme = "README.md"\n'
            'requires-python = ">=3.14"\n'
            'dependencies = []\n'
        )

    def test_author_name_only(self):
        """Author name without email produces correct authors line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp", author_name="Tim"
            )

            content = (project_path / "pyproject.toml").read_text()
            assert 'authors = [{name = "Tim"}]' in content

    def test_author_name_and_email(self):
        """Author name and email both appear in authors line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp",
                author_name="Tim", author_email="tim@example.com",
            )

            content = (project_path / "pyproject.toml").read_text()
            assert 'name = "Tim"' in content
            assert 'email = "tim@example.com"' in content

    def test_description_replaces_empty(self):
        """Description replaces the empty UV default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp", description="A cool project"
            )

            content = (project_path / "pyproject.toml").read_text()
            assert 'description = "A cool project"' in content
            assert 'description = ""' not in content

    def test_license_added(self):
        """License SPDX identifier is added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp", license_type="MIT"
            )

            content = (project_path / "pyproject.toml").read_text()
            assert 'license = "MIT"' in content

    def test_all_metadata_fields(self):
        """All metadata fields together produce correct output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp",
                author_name="Tim",
                author_email="tim@example.com",
                description="My project",
                license_type="Apache-2.0",
            )

            content = (project_path / "pyproject.toml").read_text()
            assert 'description = "My project"' in content
            assert 'name = "Tim"' in content
            assert 'email = "tim@example.com"' in content
            assert 'license = "Apache-2.0"' in content
            # Hatch config still appended
            assert '[tool.hatch.build.targets.wheel]' in content

    def test_no_metadata_leaves_file_unchanged(self):
        """No metadata fields leaves the [project] section unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            original = self._uv_pyproject()
            (project_path / "pyproject.toml").write_text(original)

            configure_pyproject(project_path, "myapp")

            content = (project_path / "pyproject.toml").read_text()
            # Original content preserved at the start
            assert 'description = ""' in content
            assert "authors" not in content
            assert 'license = ' not in content


class TestConfigurePyprojectImported:
    """Tests for configure_pyproject with imported_structure=True."""

    def _uv_pyproject(self):
        return (
            '[project]\nname = "test"\nversion = "0.1.0"\n'
            'description = ""\nreadme = "README.md"\n'
            'requires-python = ">=3.13"\ndependencies = []\n'
        )

    def test_skips_hatch_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp", imported_structure=True
            )

            content = (project_path / "pyproject.toml").read_text()
            assert "[tool.hatch.build.targets.wheel]" not in content
            assert 'packages = ["app"]' not in content

    def test_skips_entry_point(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path, "myapp", framework="flet", imported_structure=True
            )

            content = (project_path / "pyproject.toml").read_text()
            assert "[project.scripts]" not in content

    def test_still_applies_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "pyproject.toml").write_text(self._uv_pyproject())

            configure_pyproject(
                project_path,
                "myapp",
                author_name="Test Author",
                description="A test project",
                imported_structure=True,
            )

            content = (project_path / "pyproject.toml").read_text()
            assert "Test Author" in content
            assert "A test project" in content
            # But no hatch config
            assert "[tool.hatch.build.targets.wheel]" not in content
