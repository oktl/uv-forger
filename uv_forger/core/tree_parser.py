"""Parse text-based project tree structures into FolderSpec-compatible dicts.

Handles two input formats:
- Unicode box-drawing trees (├── └── │) as produced by `tree` command or tree_builder.py
- Plain indented text (spaces or tabs)

The parser is the inverse of tree_builder.py — it converts human-readable tree
text back into the normalized folder dict format used by state.folders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

# Box-drawing characters used in tree output
_BOX_CHARS = re.compile(r"[│├└─╰╭┌┘┐┤┬┴┼╮╯]")
_CONNECTOR_RE = re.compile(r"^((?:[│ ] {3})*)[├└]── ")
_CONTINUATION_RE = re.compile(r"^[│ ]*$")

_MAX_INDENT_UNIT = 8  # Cap on auto-detected indent size to handle odd formatting


@dataclass
class TreeParseResult:
    """Result of parsing a text tree structure.

    Attributes:
        folders: List of top-level folder dicts matching FolderSpec format.
        root_files: List of file names found at the project root level.
    """

    folders: list[dict[str, Any]] = field(default_factory=list)
    root_files: list[str] = field(default_factory=list)


def parse_tree_text(text: str) -> list[dict[str, Any]]:
    """Parse a text tree into a list of normalized folder dicts.

    Accepts both box-drawing trees and plain-indented text. Automatically
    detects the format and strips root wrappers when present.

    Returns:
        List of top-level folder dicts matching FolderSpec format:
        {"name": str, "create_init": bool, "root_level": bool,
         "subfolders": list, "files": list}
    """
    return _parse_tree_lines(text).folders


def parse_tree_text_full(text: str) -> TreeParseResult:
    """Parse a text tree into folders and root-level files.

    Like parse_tree_text() but also returns root-level files that would
    otherwise be dropped. Use this when importing a complete project structure.

    Returns:
        TreeParseResult with folders and root_files.
    """
    return _parse_tree_lines(text)


def _parse_tree_lines(text: str) -> TreeParseResult:
    """Shared core: strip blanks, detect format, parse, strip root, build tree."""
    if not text or not text.strip():
        return TreeParseResult()

    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return TreeParseResult()

    fmt = _detect_format(lines)
    entries = _parse_lines(lines, fmt)

    if not entries:
        return TreeParseResult()

    entries = _maybe_strip_root(entries, lines, fmt)
    return _build_tree(entries)


def _detect_format(lines: list[str]) -> Literal["box_drawing", "indented"]:
    """Detect whether lines use box-drawing characters or plain indentation."""
    for line in lines:
        if _BOX_CHARS.search(line):
            return "box_drawing"
    return "indented"


def _maybe_strip_root(
    entries: list[tuple[int, str, bool]],
    raw_lines: list[str],
    fmt: Literal["box_drawing", "indented"],
) -> list[tuple[int, str, bool]]:
    """Strip the root folder wrapper if present.

    For box-drawing: strips when the first line is a bare folder name
    (no ``├──``/``└──`` connector), like ``my_project/``. In this case
    the children are already at the correct levels (level 0 under the root).

    For plain indentation: strips when the first line is a level-0 folder
    whose children include at least one subfolder (to distinguish project
    roots like ``my_app/`` from content folders like ``core/``).
    """
    if len(entries) <= 1:
        return entries

    first_level, _first_name, first_is_folder = entries[0]
    if not first_is_folder or first_level != 0:
        return entries

    if fmt == "box_drawing":
        # Only strip if the first raw line has no box-drawing connector
        first_raw = ""
        for line in raw_lines:
            if line.strip():
                first_raw = line.rstrip()
                break
        if not first_raw or _CONNECTOR_RE.match(first_raw):
            return entries  # First line has a connector — not a bare root
        # Check for other bare (no-connector) folder lines in the raw text.
        # If present, the first line is one of multiple top-level folders
        # (e.g., "core/\n├── ...\nui/\n└── ..."), not a root wrapper.
        found_first = False
        for line in raw_lines:
            stripped = line.rstrip()
            if not stripped:
                continue
            if not found_first:
                found_first = True
                continue  # Skip first line (already identified as bare root)
            if (
                stripped.endswith("/")
                and not _CONNECTOR_RE.match(stripped)
                and not _CONTINUATION_RE.match(stripped)
            ):
                return entries  # Another bare folder — not a root wrapper
        # Bare root in box-drawing: children are at level 0 (connectors
        # have no prefix groups). Just drop the first entry.
        return entries[1:]

    # Plain indentation: only strip if ALL direct children are folders
    # (distinguishes project roots like my_app/ from content folders like core/)
    direct_children = [
        (level, name, is_folder) for level, name, is_folder in entries[1:] if level == 1
    ]
    if not direct_children:
        return entries
    all_children_are_folders = all(is_folder for _, _, is_folder in direct_children)
    if not all_children_are_folders:
        return entries

    # All subsequent entries are at level >= 1; subtract 1 from all
    if all(level > first_level for level, _, _ in entries[1:]):
        return [(level - 1, name, is_folder) for level, name, is_folder in entries[1:]]
    return entries


def _parse_lines(
    lines: list[str], fmt: Literal["box_drawing", "indented"]
) -> list[tuple[int, str, bool]]:
    """Parse all lines into (indent_level, name, is_folder) tuples."""
    if fmt == "box_drawing":
        return _parse_box_drawing_lines(lines)
    indent_size = _detect_indent_size(lines)
    return _parse_indented_lines(lines, indent_size)


def _parse_box_drawing_lines(
    lines: list[str],
) -> list[tuple[int, str, bool]]:
    """Parse box-drawing tree lines."""
    entries: list[tuple[int, str, bool]] = []

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        # Skip continuation-only lines (just │ and spaces)
        if _CONTINUATION_RE.match(stripped):
            continue

        level, name, is_folder = _parse_box_drawing_line(stripped)
        if name:
            entries.append((level, name, is_folder))

    return entries


def _parse_box_drawing_line(line: str) -> tuple[int, str, bool]:
    """Parse a single box-drawing line into (level, name, is_folder).

    The indent level is determined by counting 4-character prefix groups
    (│   or    ) before the connector (├── or └──).
    """
    match = _CONNECTOR_RE.match(line)
    if match:
        prefix = match.group(1)
        level = len(prefix) // 4
        name_part = line[match.end() :].strip()
    else:
        # First line or line without connector — level 0
        # Strip any leading box chars
        name_part = _BOX_CHARS.sub("", line).strip()
        # Also strip leftover spaces/dashes from connector removal
        name_part = name_part.lstrip("─ ").strip()
        level = 0

    is_folder = name_part.endswith("/")
    name = name_part.rstrip("/").strip()

    return level, name, is_folder


def _detect_indent_size(lines: list[str]) -> int:
    """Auto-detect the number of spaces per indent level.

    Returns 4 as default, or the indentation of the first indented line.
    Tabs are treated as 1 unit each.
    """
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        if indent > 0:
            # Check for tab indentation
            if line[0] == "\t":
                return 1  # Tabs: 1 char = 1 level
            # Use the first indented line's indentation as the unit
            return min(indent, _MAX_INDENT_UNIT)
    return 4  # Default


def _parse_indented_lines(
    lines: list[str], indent_size: int
) -> list[tuple[int, str, bool]]:
    """Parse plain-indented lines."""
    entries: list[tuple[int, str, bool]] = []

    for line in lines:
        if not line.strip():
            continue

        if line[0] == "\t":
            # Tab indentation
            indent = len(line) - len(line.lstrip("\t"))
            level = indent
        else:
            indent = len(line) - len(line.lstrip(" "))
            level = indent // indent_size if indent_size > 0 else 0

        name_part = line.strip()
        is_folder = name_part.endswith("/")
        name = name_part.rstrip("/").strip()

        if name:
            entries.append((level, name, is_folder))

    return entries


def _build_tree(entries: list[tuple[int, str, bool]]) -> TreeParseResult:
    """Build nested folder/file dicts from parsed entries using a stack.

    Uses a stack of (level, folder_dict) pairs to track the current
    parent at each nesting depth.

    Returns:
        TreeParseResult with folders and any root-level files.
    """
    root_folders: list[dict[str, Any]] = []
    root_files: list[str] = []
    # Stack: (level, folder_dict)
    stack: list[tuple[int, dict[str, Any]]] = []

    for level, name, is_folder in entries:
        # Pop stack back to find the parent for this level
        while stack and stack[-1][0] >= level:
            stack.pop()

        if is_folder:
            folder_dict: dict[str, Any] = {
                "name": name,
                "create_init": False,
                "root_level": False,
                "subfolders": [],
                "files": [],
            }

            if stack:
                # Attach as subfolder of current parent
                parent = stack[-1][1]
                parent["subfolders"].append(folder_dict)
            else:
                # Top-level folder
                root_folders.append(folder_dict)

            stack.append((level, folder_dict))
        else:
            # It's a file
            if name == "__init__.py" and stack:
                # Set create_init on parent folder instead of adding as file
                stack[-1][1]["create_init"] = True
            elif stack:
                parent = stack[-1][1]
                # Deduplicate files
                if name not in parent["files"]:
                    parent["files"].append(name)
            else:
                # Top-level file — track separately
                if name not in root_files:
                    root_files.append(name)

    return TreeParseResult(folders=root_folders, root_files=root_files)
