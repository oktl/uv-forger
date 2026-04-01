"""Test suite for filesystem_handler.py"""

import tempfile
from pathlib import Path

from uv_forger.handlers.filesystem_handler import (
    create_folders,
    setup_app_structure,
    setup_imported_structure,
)


class TestCreateFolders:
    """Tests for create_folders function"""

    def test_create_simple_string_folders(self):
        """Test create simple string folders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = ["core", "utils"]
            create_folders(parent, folders)

            assert (parent / "core").exists()
            assert (parent / "core" / "__init__.py").exists()
            assert (parent / "utils").exists()
            assert (parent / "utils" / "__init__.py").exists()

    def test_create_folder_without_init(self):
        """Test create folder without __init__.py"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [{"name": "assets", "create_init": False}]
            create_folders(parent, folders)

            assert (parent / "assets").exists()
            assert not (parent / "assets" / "__init__.py").exists()

    def test_create_folder_with_files(self):
        """Test create folder with files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [
                {
                    "name": "handlers",
                    "files": ["git_handler.py", "uv_handler.py"]
                }
            ]
            create_folders(parent, folders)

            assert (parent / "handlers" / "git_handler.py").exists()
            assert (parent / "handlers" / "uv_handler.py").exists()

    def test_create_nested_subfolders(self):
        """Test create nested subfolders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [
                {
                    "name": "app",
                    "subfolders": [
                        "core",
                        {"name": "utils", "subfolders": ["helpers"]}
                    ]
                }
            ]
            create_folders(parent, folders)

            assert (parent / "app").exists()
            assert (parent / "app" / "core").exists()
            assert (parent / "app" / "core" / "__init__.py").exists()
            assert (parent / "app" / "utils").exists()
            assert (parent / "app" / "utils" / "helpers").exists()

    def test_parent_create_init_propagation(self):
        """Test parent create_init propagation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [
                {
                    "name": "no_init",
                    "create_init": False,
                    "subfolders": ["child"]
                }
            ]
            create_folders(parent, folders)

            assert (parent / "no_init").exists()
            assert not (parent / "no_init" / "__init__.py").exists()
            assert (parent / "no_init" / "child").exists()
            assert not (parent / "no_init" / "child" / "__init__.py").exists()


class TestSetupAppStructure:
    """Tests for setup_app_structure function"""

    def test_basic_app_structure(self):
        """Test basic app structure creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            folders = ["core", "utils"]
            setup_app_structure(project_path, folders)

            assert (project_path / "app").exists()
            assert (project_path / "app" / "__init__.py").exists()
            assert (project_path / "app" / "core").exists()
            assert (project_path / "app" / "utils").exists()

    def test_root_level_folders(self):
        """Test root-level folders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            folders = [
                {"name": "tests", "root_level": True},
                "core"
            ]
            setup_app_structure(project_path, folders)

            assert (project_path / "tests").exists()
            assert (project_path / "app" / "core").exists()
            assert not (project_path / "app" / "tests").exists()

    def test_main_py_moved_to_app(self):
        """Test main.py moved to app/main.py"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "main.py").write_text("# main file")

            setup_app_structure(project_path, [])

            assert not (project_path / "main.py").exists()
            assert (project_path / "app" / "main.py").exists()
            assert (project_path / "app" / "main.py").read_text() == "# main file"

    def test_works_without_main_py(self):
        """Test works without main.py"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            setup_app_structure(project_path, [])

            assert (project_path / "app").exists()


class TestCreateFoldersSkipFiles:
    """Tests for create_folders with skip_files=True."""

    def test_skip_files_skips_template_files(self):
        """When skip_files=True, template files in 'files' lists are not created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [
                {
                    "name": "core",
                    "files": ["state.py", "models.py"],
                }
            ]
            create_folders(parent, folders, skip_files=True)

            assert (parent / "core").exists()
            assert (parent / "core" / "__init__.py").exists()
            assert not (parent / "core" / "state.py").exists()
            assert not (parent / "core" / "models.py").exists()

    def test_skip_files_still_creates_init(self):
        """When skip_files=True, __init__.py is still created (it's directory infrastructure)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [
                {
                    "name": "handlers",
                    "create_init": True,
                    "files": ["event_handlers.py"],
                    "subfolders": ["utils"],
                }
            ]
            create_folders(parent, folders, skip_files=True)

            assert (parent / "handlers" / "__init__.py").exists()
            assert (parent / "handlers" / "utils" / "__init__.py").exists()
            assert not (parent / "handlers" / "event_handlers.py").exists()

    def test_skip_files_propagates_to_subfolders(self):
        """skip_files is passed through to nested subfolder creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [
                {
                    "name": "core",
                    "subfolders": [
                        {"name": "utils", "files": ["helper.py"]}
                    ],
                }
            ]
            create_folders(parent, folders, skip_files=True)

            assert (parent / "core" / "utils").exists()
            assert not (parent / "core" / "utils" / "helper.py").exists()

    def test_setup_app_structure_skip_files(self):
        """setup_app_structure passes skip_files through to create_folders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            folders = [{"name": "utils", "files": ["constants.py"]}]
            setup_app_structure(project_path, folders, skip_files=True)

            assert (project_path / "app" / "utils").exists()
            assert (project_path / "app" / "utils" / "__init__.py").exists()
            assert not (project_path / "app" / "utils" / "constants.py").exists()


class TestCreateFoldersWithResolver:
    """Tests for create_folders with a BoilerplateResolver."""

    def _make_resolver(self, tmpdir, files=None):
        """Create a BoilerplateResolver with common boilerplate files."""
        from uv_forger.core.boilerplate_resolver import BoilerplateResolver

        bp = Path(tmpdir) / "bp" / "common"
        bp.mkdir(parents=True)
        for name, content in (files or {}).items():
            (bp / name).write_text(content)
        return BoilerplateResolver(
            "testproj", boilerplate_dir=Path(tmpdir) / "bp"
        )

    def test_file_gets_boilerplate_content(self):
        """Files with matching boilerplate get their content populated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"state.py": "# boilerplate for {{project_name}}"}
            )
            parent = Path(tmpdir) / "project"
            parent.mkdir()
            folders = [{"name": "core", "files": ["state.py"]}]
            create_folders(parent, folders, resolver=resolver)

            created = parent / "core" / "state.py"
            assert created.exists()
            assert created.read_text() == "# boilerplate for Testproj"

    def test_file_empty_when_resolver_returns_none(self):
        """Files without matching boilerplate are created empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(tmpdir)
            parent = Path(tmpdir) / "project"
            parent.mkdir()
            folders = [{"name": "core", "files": ["unknown.py"]}]
            create_folders(parent, folders, resolver=resolver)

            created = parent / "core" / "unknown.py"
            assert created.exists()
            assert created.read_text() == ""

    def test_backward_compatible_without_resolver(self):
        """create_folders works unchanged when resolver is not passed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            folders = [{"name": "core", "files": ["models.py"]}]
            create_folders(parent, folders)

            created = parent / "core" / "models.py"
            assert created.exists()
            assert created.read_text() == ""

    def test_resolver_propagates_to_subfolders(self):
        """Resolver is passed through to nested subfolder creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"helper.py": "# helper"}
            )
            parent = Path(tmpdir) / "project"
            parent.mkdir()
            folders = [
                {
                    "name": "core",
                    "subfolders": [
                        {"name": "utils", "files": ["helper.py"]}
                    ],
                }
            ]
            create_folders(parent, folders, resolver=resolver)

            created = parent / "core" / "utils" / "helper.py"
            assert created.exists()
            assert created.read_text() == "# helper"

    def test_setup_app_structure_with_resolver(self):
        """setup_app_structure passes resolver through to create_folders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"constants.py": "APP = '{{project_name}}'"}
            )
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            folders = [{"name": "utils", "files": ["constants.py"]}]
            setup_app_structure(project_path, folders, resolver=resolver)

            created = project_path / "app" / "utils" / "constants.py"
            assert created.exists()
            assert created.read_text() == "APP = 'Testproj'"

    def test_setup_app_structure_replaces_uv_main_with_boilerplate(self):
        """UV's default main.py is replaced by boilerplate main.py if available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"main.py": "# {{project_name}} app entry point"}
            )
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            # Simulate uv init creating a default main.py
            (project_path / "main.py").write_text('print("Hello")')
            setup_app_structure(project_path, [], resolver=resolver)

            app_main = project_path / "app" / "main.py"
            assert app_main.exists()
            assert app_main.read_text() == "# Testproj app entry point"

    def test_setup_app_structure_keeps_uv_main_without_boilerplate(self):
        """UV's default main.py is kept when no boilerplate main.py exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(tmpdir)  # no main.py boilerplate
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            (project_path / "main.py").write_text('print("Hello")')
            setup_app_structure(project_path, [], resolver=resolver)

            app_main = project_path / "app" / "main.py"
            assert app_main.exists()
            assert app_main.read_text() == 'print("Hello")'

    def test_setup_app_structure_no_replace_when_skip_files(self):
        """main.py is not replaced when skip_files=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"main.py": "# boilerplate"}
            )
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            (project_path / "main.py").write_text('print("Hello")')
            setup_app_structure(
                project_path, [], resolver=resolver, skip_files=True,
            )

            app_main = project_path / "app" / "main.py"
            assert app_main.exists()
            assert app_main.read_text() == 'print("Hello")'

    def test_setup_app_structure_replaces_readme_with_boilerplate(self):
        """UV's empty README.md is replaced by boilerplate if available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"README.md": "# {{project_name}}\n\nA great project."}
            )
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            # Simulate uv init creating an empty README.md
            (project_path / "README.md").touch()
            setup_app_structure(project_path, [], resolver=resolver)

            readme = project_path / "README.md"
            assert readme.exists()
            assert readme.read_text() == "# Testproj\n\nA great project."

    def test_setup_app_structure_keeps_readme_without_boilerplate(self):
        """UV's README.md is kept when no boilerplate README exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(tmpdir)  # no README boilerplate
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            (project_path / "README.md").write_text("# existing")
            setup_app_structure(project_path, [], resolver=resolver)

            readme = project_path / "README.md"
            assert readme.read_text() == "# existing"

    def test_setup_app_structure_no_readme_replace_when_skip_files(self):
        """README.md is not replaced when skip_files=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = self._make_resolver(
                tmpdir, {"README.md": "# boilerplate readme"}
            )
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()
            (project_path / "README.md").touch()
            setup_app_structure(
                project_path, [], resolver=resolver, skip_files=True,
            )

            readme = project_path / "README.md"
            assert readme.read_text() == ""


class TestSetupImportedStructure:
    """Tests for setup_imported_structure — imported tree builds at project root."""

    def test_no_app_directory_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            setup_imported_structure(project, [{"name": "src", "create_init": False}])
            assert not (project / "app").exists()
            assert (project / "src").exists()

    def test_folders_created_at_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            folders = [
                {"name": "docs", "create_init": False, "files": ["index.md"]},
                {"name": "src", "create_init": False, "subfolders": [
                    {"name": "mylib", "create_init": True, "files": ["app.py"]}
                ]},
                {"name": "tests", "create_init": False, "files": ["test_main.py"]},
            ]
            setup_imported_structure(project, folders)

            assert (project / "docs").is_dir()
            assert (project / "docs" / "index.md").exists()
            assert (project / "src" / "mylib").is_dir()
            assert (project / "src" / "mylib" / "__init__.py").exists()
            assert (project / "src" / "mylib" / "app.py").exists()
            assert (project / "tests" / "test_main.py").exists()

    def test_uv_main_py_deleted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            (project / "main.py").write_text('print("hello")')
            setup_imported_structure(project, [{"name": "src"}])
            assert not (project / "main.py").exists()

    def test_root_files_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            root_files = ["CHANGELOG.md", "LICENSE", "CONTRIBUTING.md"]
            setup_imported_structure(project, [], root_files=root_files)

            for f in root_files:
                assert (project / f).exists()

    def test_uv_generated_files_skipped_without_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            # Simulate UV-generated files
            (project / "pyproject.toml").write_text("[project]")
            (project / "README.md").write_text("# readme")

            root_files = ["pyproject.toml", "README.md", ".gitignore", "LICENSE"]
            setup_imported_structure(project, [], root_files=root_files)

            # UV files should NOT be overwritten when no override
            assert (project / "pyproject.toml").read_text() == "[project]"
            assert (project / "README.md").read_text() == "# readme"
            # Non-UV files should be created
            assert (project / "LICENSE").exists()

    def test_uv_generated_files_overridden_with_user_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            # Simulate UV-generated files
            (project / "pyproject.toml").write_text("[project]\nname = 'auto'")
            (project / "README.md").write_text("# Auto readme")

            overrides = {
                "pyproject.toml": '[project]\nname = "custom"',
                "README.md": "# Custom Readme\n\nMy project.",
            }
            root_files = ["pyproject.toml", "README.md", "LICENSE"]
            setup_imported_structure(
                project, [], root_files=root_files, file_overrides=overrides
            )

            # UV files with overrides should be replaced
            assert (project / "pyproject.toml").read_text() == '[project]\nname = "custom"'
            assert (project / "README.md").read_text() == "# Custom Readme\n\nMy project."
            # Non-UV files without overrides still created
            assert (project / "LICENSE").exists()

    def test_file_overrides_for_root_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            overrides = {"LICENSE": "MIT License\nCopyright 2024"}
            setup_imported_structure(
                project, [], root_files=["LICENSE"], file_overrides=overrides
            )
            assert (project / "LICENSE").read_text() == "MIT License\nCopyright 2024"

    def test_file_overrides_for_folder_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            folders = [{"name": "src", "create_init": False, "files": ["app.py"]}]
            overrides = {"src/app.py": "# my app code"}
            setup_imported_structure(project, folders, file_overrides=overrides)
            assert (project / "src" / "app.py").read_text() == "# my app code"

    def test_skip_files_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            folders = [{"name": "src", "files": ["app.py"]}]
            setup_imported_structure(
                project, folders, root_files=["LICENSE"], skip_files=True
            )
            # Directories created, but files skipped
            assert (project / "src").is_dir()
            assert not (project / "src" / "app.py").exists()
            assert not (project / "LICENSE").exists()
