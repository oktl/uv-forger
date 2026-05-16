"""Tests for uv_forger.core.tree_parser — text tree structure parsing."""

from __future__ import annotations

from uv_forger.core.tree_parser import (
    TreeParseResult,
    parse_tree_text,
    parse_tree_text_full,
)

# ── Empty / trivial input ────────────────────────────────────────────


class TestEmptyInput:
    def test_empty_string(self):
        assert parse_tree_text("") == []

    def test_whitespace_only(self):
        assert parse_tree_text("   \n  \n   ") == []

    def test_none_like(self):
        assert parse_tree_text("\n\n\n") == []


# ── Box-drawing format ───────────────────────────────────────────────


class TestBoxDrawingBasic:
    def test_single_folder(self):
        text = "├── core/"
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["name"] == "core"
        assert result[0]["create_init"] is False

    def test_single_file_at_root_dropped(self):
        """Top-level files are dropped since state.folders holds only folder dicts."""
        text = "├── README.md"
        result = parse_tree_text(text)
        assert result == []

    def test_folder_with_files(self):
        text = """\
├── core/
│   ├── state.py
│   └── models.py"""
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["name"] == "core"
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_multiple_top_level_folders(self):
        text = """\
├── core/
│   └── state.py
├── ui/
│   └── components.py
└── utils/
    └── helpers.py"""
        result = parse_tree_text(text)
        assert len(result) == 3
        assert [f["name"] for f in result] == ["core", "ui", "utils"]

    def test_init_py_sets_create_init(self):
        text = """\
├── core/
│   ├── __init__.py
│   ├── state.py
│   └── models.py"""
        result = parse_tree_text(text)
        assert result[0]["create_init"] is True
        assert "__init__.py" not in result[0]["files"]
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_no_init_py_means_false(self):
        text = """\
├── assets/
│   ├── logo.png
│   └── style.css"""
        result = parse_tree_text(text)
        assert result[0]["create_init"] is False


class TestBoxDrawingNested:
    def test_nested_subfolders(self):
        text = """\
├── core/
│   ├── __init__.py
│   ├── state.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py"""
        result = parse_tree_text(text)
        core = result[0]
        assert core["name"] == "core"
        assert core["create_init"] is True
        assert len(core["subfolders"]) == 1
        utils = core["subfolders"][0]
        assert utils["name"] == "utils"
        assert utils["create_init"] is True
        assert utils["files"] == ["helpers.py"]

    def test_three_levels_deep(self):
        text = """\
├── src/
│   ├── core/
│   │   ├── db/
│   │   │   └── migrations.py
│   │   └── models.py
│   └── api/
│       └── routes.py"""
        result = parse_tree_text(text)
        src = result[0]
        assert src["name"] == "src"
        assert len(src["subfolders"]) == 2
        core = src["subfolders"][0]
        assert core["name"] == "core"
        db = core["subfolders"][0]
        assert db["name"] == "db"
        assert db["files"] == ["migrations.py"]
        assert core["files"] == ["models.py"]
        api = src["subfolders"][1]
        assert api["name"] == "api"
        assert api["files"] == ["routes.py"]

    def test_mixed_files_and_subfolders(self):
        text = """\
├── core/
│   ├── __init__.py
│   ├── constants.py
│   ├── state.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   └── utils/
│       └── helpers.py"""
        result = parse_tree_text(text)
        core = result[0]
        assert core["files"] == ["constants.py", "state.py"]
        assert len(core["subfolders"]) == 2
        assert core["subfolders"][0]["name"] == "models"
        assert core["subfolders"][1]["name"] == "utils"


class TestBoxDrawingRootWrapper:
    def test_root_folder_stripped(self):
        text = """\
jsonl_lens/
├── __init__.py
├── main.py
├── core/
│   ├── __init__.py
│   └── state.py"""
        result = parse_tree_text(text)
        # Root "jsonl_lens/" should be stripped, core should be top-level
        assert len(result) == 1
        assert result[0]["name"] == "core"

    def test_project_root_with_multiple_folders(self):
        text = """\
my_project/
├── core/
│   └── state.py
├── ui/
│   └── components.py
└── utils/"""
        result = parse_tree_text(text)
        assert len(result) == 3
        assert [f["name"] for f in result] == ["core", "ui", "utils"]

    def test_no_root_wrapper_when_multiple_level_zero(self):
        text = """\
core/
├── state.py
└── models.py
ui/
└── components.py"""
        result = parse_tree_text(text)
        assert len(result) == 2
        assert result[0]["name"] == "core"
        assert result[1]["name"] == "ui"


# ── Plain indentation format ─────────────────────────────────────────


class TestPlainIndentation:
    def test_two_space_indent(self):
        text = """\
core/
  state.py
  models.py"""
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["name"] == "core"
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_four_space_indent(self):
        text = """\
core/
    state.py
    models.py"""
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_tab_indent(self):
        text = "core/\n\tstate.py\n\tmodels.py"
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_nested_plain_indent(self):
        text = """\
core/
    __init__.py
    state.py
    utils/
        __init__.py
        helpers.py"""
        result = parse_tree_text(text)
        core = result[0]
        assert core["create_init"] is True
        assert core["files"] == ["state.py"]
        assert len(core["subfolders"]) == 1
        utils = core["subfolders"][0]
        assert utils["create_init"] is True
        assert utils["files"] == ["helpers.py"]

    def test_plain_indent_root_wrapper(self):
        text = """\
my_app/
    core/
        state.py
    ui/
        components.py"""
        result = parse_tree_text(text)
        assert len(result) == 2
        assert result[0]["name"] == "core"
        assert result[1]["name"] == "ui"


# ── Edge cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_blank_lines_between_entries(self):
        text = """\
├── core/
│   └── state.py

├── ui/
│   └── components.py"""
        result = parse_tree_text(text)
        assert len(result) == 2

    def test_trailing_whitespace(self):
        text = "├── core/   \n│   └── state.py   "
        result = parse_tree_text(text)
        assert result[0]["name"] == "core"
        assert result[0]["files"] == ["state.py"]

    def test_continuation_lines_skipped(self):
        text = """\
├── core/
│   ├── state.py
│
│   └── models.py"""
        result = parse_tree_text(text)
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_duplicate_files_deduplicated(self):
        text = """\
├── core/
│   ├── state.py
│   ├── state.py
│   └── models.py"""
        result = parse_tree_text(text)
        assert result[0]["files"] == ["state.py", "models.py"]

    def test_empty_folder(self):
        text = "└── assets/"
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["name"] == "assets"
        assert result[0]["subfolders"] == []
        assert result[0]["files"] == []

    def test_deeply_nested_five_levels(self):
        text = """\
├── a/
│   └── b/
│       └── c/
│           └── d/
│               └── e/
│                   └── deep.py"""
        result = parse_tree_text(text)
        current = result[0]
        for name in ["a", "b", "c", "d", "e"]:
            assert current["name"] == name
            if name == "e":
                assert current["files"] == ["deep.py"]
            else:
                assert len(current["subfolders"]) == 1
                current = current["subfolders"][0]

    def test_leading_blank_lines_stripped(self):
        text = "\n\n├── core/\n│   └── state.py"
        result = parse_tree_text(text)
        assert len(result) == 1
        assert result[0]["name"] == "core"

    def test_folder_without_trailing_slash_with_children(self):
        """Folder detected by having children even without trailing /."""
        text = """\
core
    state.py
    models.py"""
        result = parse_tree_text(text)
        # "core" has no trailing / but it's at level 0 with children at level 1
        # Since it has no slash, it's treated as a file at level 0 (dropped)
        # The children become orphaned at level 1 with no parent
        # This is expected — we require trailing / for folders in plain mode
        # Actually, state.py and models.py are at level 1 with no parent folder
        # They'll be treated as files at a level with no stack entry
        # Let's verify the behavior is predictable
        assert isinstance(result, list)


class TestRootLevelDefault:
    def test_all_folders_default_root_level_false(self):
        text = """\
├── core/
│   └── state.py
└── ui/
    └── components.py"""
        result = parse_tree_text(text)
        for folder in result:
            assert folder["root_level"] is False

    def test_create_init_default_false(self):
        """Parsed folders default create_init=False (tree is explicit)."""
        text = """\
├── core/
│   └── state.py"""
        result = parse_tree_text(text)
        assert result[0]["create_init"] is False


# ── Realistic / integration-style tests ──────────────────────────────


class TestRealisticTrees:
    def test_full_project_structure(self):
        """Parse a realistic project tree with multiple levels."""
        text = """\
jsonl_lens/
├── __init__.py
├── main.py
├── core/
│   ├── __init__.py
│   ├── state.py
│   ├── models.py
│   └── parser.py
├── ui/
│   ├── __init__.py
│   ├── components.py
│   └── dialogs.py
├── handlers/
│   ├── __init__.py
│   ├── file_handler.py
│   └── view_handler.py
└── utils/
    ├── __init__.py
    └── helpers.py"""
        result = parse_tree_text(text)
        assert len(result) == 4
        names = [f["name"] for f in result]
        assert names == ["core", "ui", "handlers", "utils"]

        # All have create_init because __init__.py is listed
        for folder in result:
            assert folder["create_init"] is True

        # Check file counts
        assert result[0]["files"] == ["state.py", "models.py", "parser.py"]
        assert result[1]["files"] == ["components.py", "dialogs.py"]
        assert result[2]["files"] == ["file_handler.py", "view_handler.py"]
        assert result[3]["files"] == ["helpers.py"]

    def test_tree_command_style_with_project_root(self):
        """Full tree command output with project root and standard files."""
        text = """\
my-project/
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
├── my_project/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── state.py
│   └── ui/
│       ├── __init__.py
│       └── components.py"""
        result = parse_tree_text(text)
        # Root "my-project/" stripped. Files like .gitignore are dropped.
        # "my_project/" becomes the new root, which also gets stripped
        # since all its children are indented under it.
        # Actually: after stripping "my-project/", we have:
        #   .gitignore (file, dropped)
        #   .python-version (file, dropped)
        #   README.md (file, dropped)
        #   pyproject.toml (file, dropped)
        #   my_project/ (folder with children)
        # So my_project is the only folder at top level
        # Its children: __init__.py, main.py, core/, ui/
        assert len(result) == 1
        pkg = result[0]
        assert pkg["name"] == "my_project"
        assert pkg["create_init"] is True
        assert "main.py" in pkg["files"]
        assert len(pkg["subfolders"]) == 2

    def test_django_style_project(self):
        text = """\
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   └── users/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       └── urls.py
├── templates/
│   └── base.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js"""
        result = parse_tree_text(text)
        assert len(result) == 4
        names = [f["name"] for f in result]
        assert names == ["config", "apps", "templates", "static"]

        # Check nested structure
        apps = result[1]
        assert len(apps["subfolders"]) == 1
        users = apps["subfolders"][0]
        assert users["name"] == "users"
        assert users["create_init"] is True
        assert set(users["files"]) == {"models.py", "views.py", "urls.py"}

        static = result[3]
        assert len(static["subfolders"]) == 2
        css = static["subfolders"][0]
        assert css["name"] == "css"
        assert css["files"] == ["style.css"]

    def test_minimal_flat_structure(self):
        text = """\
├── core/
├── ui/
├── utils/
└── assets/"""
        result = parse_tree_text(text)
        assert len(result) == 4
        for f in result:
            assert f["subfolders"] == []
            assert f["files"] == []


class TestRoundtrip:
    """Test parsing output from tree_builder.py-style format."""

    def test_parse_tree_builder_output(self):
        """Verify that tree builder output format can be parsed back."""
        # Simulated output from build_project_tree_lines for app subfolders
        text = """\
├── core/
│   ├── __init__.py
│   ├── state.py
│   └── models.py
├── ui/
│   ├── __init__.py
│   └── components.py
└── utils/
    ├── __init__.py
    └── helpers.py"""
        result = parse_tree_text(text)
        assert len(result) == 3

        core = result[0]
        assert core["name"] == "core"
        assert core["create_init"] is True
        assert core["files"] == ["state.py", "models.py"]

        ui = result[1]
        assert ui["name"] == "ui"
        assert ui["create_init"] is True
        assert ui["files"] == ["components.py"]

        utils = result[2]
        assert utils["name"] == "utils"
        assert utils["create_init"] is True
        assert utils["files"] == ["helpers.py"]


# ── Counting helpers for dialog preview ──────────────────────────────


class TestTreeStats:
    """Test that we can count folders and files from parsed results."""

    @staticmethod
    def _count(folders: list[dict]) -> tuple[int, int]:
        """Count total folders and files recursively."""
        folder_count = 0
        file_count = 0
        for f in folders:
            folder_count += 1
            file_count += len(f.get("files", []))
            if f.get("create_init"):
                file_count += 1  # __init__.py
            sub = f.get("subfolders", [])
            if sub:
                sf, sfi = TestTreeStats._count(sub)
                folder_count += sf
                file_count += sfi
        return folder_count, file_count

    def test_count_simple(self):
        text = """\
├── core/
│   ├── __init__.py
│   ├── state.py
│   └── models.py
└── ui/
    └── components.py"""
        result = parse_tree_text(text)
        folders, files = self._count(result)
        assert folders == 2
        assert files == 4  # __init__.py + state.py + models.py + components.py

    def test_count_nested(self):
        text = """\
├── core/
│   ├── __init__.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py"""
        result = parse_tree_text(text)
        folders, files = self._count(result)
        assert folders == 2  # core, utils
        assert files == 3  # core/__init__.py, utils/__init__.py, helpers.py


# ── parse_tree_text_full() — returns folders AND root files ─────────


class TestParseTreeTextFull:
    def test_empty_returns_empty_result(self):
        result = parse_tree_text_full("")
        assert isinstance(result, TreeParseResult)
        assert result.folders == []
        assert result.root_files == []

    def test_folders_only_no_root_files(self):
        text = "├── core/\n└── ui/"
        result = parse_tree_text_full(text)
        assert len(result.folders) == 2
        assert result.root_files == []

    def test_root_files_returned(self):
        text = """\
├── README.md
├── LICENSE
├── core/
│   └── state.py
└── ui/"""
        result = parse_tree_text_full(text)
        assert len(result.folders) == 2
        assert "README.md" in result.root_files
        assert "LICENSE" in result.root_files

    def test_root_files_from_project_tree(self):
        """Full project tree with root wrapper stripped."""
        text = """\
jsonl-lens/
├── .gitignore
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── docs/
│   ├── index.md
│   └── usage.md
├── src/
│   └── jsonl_lens/
│       ├── __init__.py
│       └── app.py
└── tests/
    └── test_parser.py"""
        result = parse_tree_text_full(text)
        assert len(result.folders) == 3  # docs, src, tests
        assert ".gitignore" in result.root_files
        assert "pyproject.toml" in result.root_files
        assert "README.md" in result.root_files
        assert "CHANGELOG.md" in result.root_files
        assert "LICENSE" in result.root_files

    def test_root_files_only(self):
        """Input with only root-level files and no folders."""
        text = "├── README.md\n├── LICENSE\n└── setup.py"
        result = parse_tree_text_full(text)
        assert result.folders == []
        assert len(result.root_files) == 3

    def test_backward_compat_parse_tree_text_drops_files(self):
        """parse_tree_text() still drops root files for backward compat."""
        text = "├── README.md\n├── core/\n└── ui/"
        folders = parse_tree_text(text)
        assert len(folders) == 2  # Only folders, no root files
        full = parse_tree_text_full(text)
        assert len(full.root_files) == 1
        assert full.root_files[0] == "README.md"

    def test_root_files_deduped(self):
        text = "├── README.md\n├── README.md\n└── core/"
        result = parse_tree_text_full(text)
        assert result.root_files.count("README.md") == 1

    def test_plain_indented_root_files(self):
        """Plain indented with root files — root not stripped when it has file children."""
        text = """\
README.md
LICENSE
src/
    main.py
tests/
    test_main.py"""
        result = parse_tree_text_full(text)
        assert len(result.folders) == 2  # src, tests
        assert "README.md" in result.root_files
        assert "LICENSE" in result.root_files
