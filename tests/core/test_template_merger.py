"""Tests for template_merger.py - folder normalization and merging utilities."""

from uv_forger.core.models import FolderSpec
from uv_forger.core.template_merger import (
    _merge_files,
    merge_folder_lists,
    normalize_folder,
)

# ========== TestNormalizeFolder ==========


class TestNormalizeFolder:
    """Tests for normalize_folder()."""

    def test_string_input(self):
        result = normalize_folder("core")
        assert result == {
            "name": "core",
            "create_init": True,
            "root_level": False,
            "subfolders": [],
            "files": [],
        }

    def test_minimal_dict(self):
        result = normalize_folder({"name": "ui"})
        assert result["name"] == "ui"
        assert result["create_init"] is True
        assert result["root_level"] is False
        assert result["subfolders"] == []
        assert result["files"] == []

    def test_full_dict(self):
        result = normalize_folder(
            {
                "name": "config",
                "create_init": False,
                "root_level": True,
                "subfolders": ["sub1"],
                "files": ["settings.py"],
            }
        )
        assert result["name"] == "config"
        assert result["create_init"] is False
        assert result["root_level"] is True
        assert len(result["subfolders"]) == 1
        assert result["subfolders"][0]["name"] == "sub1"
        assert result["files"] == ["settings.py"]

    def test_nested_subfolders(self):
        result = normalize_folder(
            {
                "name": "app",
                "subfolders": [{"name": "core", "subfolders": ["deep"]}],
            }
        )
        assert result["subfolders"][0]["name"] == "core"
        assert result["subfolders"][0]["subfolders"][0]["name"] == "deep"

    def test_folderspec_input(self):
        spec = FolderSpec(
            name="handlers",
            create_init=True,
            root_level=False,
            subfolders=["sub"],
            files=["event.py", "factory.py"],
        )
        result = normalize_folder(spec)
        assert result["name"] == "handlers"
        assert result["create_init"] is True
        assert result["root_level"] is False
        assert len(result["subfolders"]) == 1
        assert result["subfolders"][0]["name"] == "sub"
        assert result["files"] == ["event.py", "factory.py"]

    def test_folderspec_none_subfolders_and_files(self):
        spec = FolderSpec(name="empty", subfolders=None, files=None)
        result = normalize_folder(spec)
        assert result["subfolders"] == []
        assert result["files"] == []

    def test_dict_none_subfolders_and_files(self):
        result = normalize_folder({"name": "x", "subfolders": None, "files": None})
        assert result["subfolders"] == []
        assert result["files"] == []


# ========== TestMergeFiles ==========


class TestMergeFiles:
    """Tests for _merge_files()."""

    def test_disjoint_lists(self):
        result = _merge_files(["a.py", "b.py"], ["c.py", "d.py"])
        assert result == ["a.py", "b.py", "c.py", "d.py"]

    def test_identical_lists(self):
        result = _merge_files(["a.py", "b.py"], ["a.py", "b.py"])
        assert result == ["a.py", "b.py"]

    def test_partial_overlap(self):
        result = _merge_files(["a.py", "b.py"], ["b.py", "c.py"])
        assert result == ["a.py", "b.py", "c.py"]

    def test_empty_primary(self):
        result = _merge_files([], ["a.py", "b.py"])
        assert result == ["a.py", "b.py"]

    def test_both_empty(self):
        result = _merge_files([], [])
        assert result == []


# ========== TestMergeFolderLists ==========


class TestMergeFolderLists:
    """Tests for merge_folder_lists()."""

    def test_both_empty(self):
        assert merge_folder_lists([], []) == []

    def test_empty_secondary(self):
        result = merge_folder_lists(["core", "ui"], [])
        assert len(result) == 2
        assert result[0]["name"] == "core"
        assert result[1]["name"] == "ui"

    def test_empty_primary(self):
        result = merge_folder_lists([], ["api", "models"])
        assert len(result) == 2
        assert result[0]["name"] == "api"
        assert result[1]["name"] == "models"

    def test_no_overlap(self):
        result = merge_folder_lists(["core", "ui"], ["api", "models"])
        assert len(result) == 4
        names = [f["name"] for f in result]
        assert names == ["core", "ui", "api", "models"]

    def test_full_overlap(self):
        result = merge_folder_lists(["core", "utils"], ["core", "utils"])
        assert len(result) == 2
        names = [f["name"] for f in result]
        assert names == ["core", "utils"]

    def test_partial_overlap(self):
        result = merge_folder_lists(["core", "ui"], ["core", "api"])
        assert len(result) == 3
        names = [f["name"] for f in result]
        assert names == ["core", "ui", "api"]

    def test_primary_order_preserved(self):
        result = merge_folder_lists(
            ["zebra", "alpha", "middle"],
            ["beta", "alpha"],
        )
        names = [f["name"] for f in result]
        assert names == ["zebra", "alpha", "middle", "beta"]

    def test_root_level_or_logic(self):
        primary = [{"name": "tests", "root_level": False}]
        secondary = [{"name": "tests", "root_level": True}]
        result = merge_folder_lists(primary, secondary)
        assert result[0]["root_level"] is True

    def test_create_init_or_logic(self):
        primary = [{"name": "static", "create_init": False}]
        secondary = [{"name": "static", "create_init": True}]
        result = merge_folder_lists(primary, secondary)
        assert result[0]["create_init"] is True

    def test_recursive_subfolders(self):
        primary = [
            {"name": "app", "subfolders": [{"name": "core", "files": ["state.py"]}]}
        ]
        secondary = [
            {
                "name": "app",
                "subfolders": [
                    {"name": "core", "files": ["models.py"]},
                    {"name": "api", "files": []},
                ],
            }
        ]
        result = merge_folder_lists(primary, secondary)
        assert len(result) == 1
        app = result[0]
        assert app["name"] == "app"
        assert len(app["subfolders"]) == 2
        core = app["subfolders"][0]
        assert core["name"] == "core"
        assert "state.py" in core["files"]
        assert "models.py" in core["files"]
        assert app["subfolders"][1]["name"] == "api"

    def test_files_union(self):
        primary = [{"name": "config", "files": ["settings.py", "urls.py"]}]
        secondary = [{"name": "config", "files": ["urls.py", "wsgi.py"]}]
        result = merge_folder_lists(primary, secondary)
        assert result[0]["files"] == ["settings.py", "urls.py", "wsgi.py"]

    def test_mixed_string_and_dict(self):
        result = merge_folder_lists(
            ["core"],
            [{"name": "core", "files": ["state.py"], "subfolders": []}],
        )
        assert len(result) == 1
        assert result[0]["name"] == "core"
        assert result[0]["files"] == ["state.py"]

    def test_folderspec_in_primary(self):
        spec = FolderSpec(name="utils", files=["helpers.py"])
        result = merge_folder_lists(
            [spec],
            [{"name": "utils", "files": ["constants.py"]}],
        )
        assert len(result) == 1
        assert "helpers.py" in result[0]["files"]
        assert "constants.py" in result[0]["files"]
