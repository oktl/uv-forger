# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0]

Flet 0.86.5 upgrade and a partial move to Flet's declarative (`@ft.component`) style, plus a
round of dead-code removal. No user-facing feature changes — the UI behaves as it did in 0.4.0.

### Changed

- Flet 0.82.2 → 0.86.5, with `flet-code-editor` in lockstep (it pins Flet exactly) and
  `fce-enhanced` → 0.2.2. Brings 3.2–6.7× faster control diffing and smarter `.update()`
- `AppState` is now `@ft.observable`; imperative code keeps working. Three consequences needed
  handling and are pinned by 12 new tests: sets are not wrapped by Flet (so `dev_packages`
  rebinds instead of mutating), `dataclasses.asdict()` raises on the wrappers (added
  `models.to_plain()` at the preset/history boundary), and `reset()` was assigning a throwaway
  instance's collections
- Packages display converted to a declarative component (`ui/packages_panel.py`) — the imperative
  rebuild of the container's `.controls` list is gone, and rendering is one pure function of state
- Project structure display converted to a declarative component (`ui/folders_panel.py`) — root
  files, folders, nested subfolders, selection, override indicator, and both context menus.
  Replaces `_create_item_container` (88 lines) and `_process_folder_recursive`
- `get_canonical_file_path()` moved from `handlers/folder_handlers.py` to `core/models.py`; it is
  a pure function over folder dicts and the UI layer needs it
- Refactoring pass across `core/` and `handlers/`: duplication removed, helpers merged, dead code
  deleted (~700 lines net)
- CI: `actions/checkout` → v5, `astral-sh/setup-uv` → v7
- 781 tests, up from 776

### Fixed

- File editor, broken by the Flet upgrade. `fce-enhanced` 0.1.6 set `self._dirty = False` on an
  `ft.Column` subclass, colliding with Flet's reserved `BaseControl._dirty` dict (new in 0.83)
  and blowing up the next `page.update()` on a mounted tree. Fixed upstream by extending
  `EditorHandle`; uv-forger now drives the editor through the public handle instead of 15
  private members
- Pinned `pygments < 2.20`, which was breaking code blocks in the docs site

## [0.4.0]

### Added

- Import tree structure from text — paste a box-drawing or indented text tree to define a complete
  project layout (folders, subfolders, files, and root-level files)
- Import dialog with live preview showing parsed folder/file/root-file counts
- Replace or Merge import modes — replace current structure entirely or merge with existing folders
- Root-level files from imported trees displayed individually in the main window folder display
  (selectable, editable, deletable)
- Root file content editing — edit imported root files (including UV-generated files like
  pyproject.toml, README.md) before build; edited content overrides UV defaults
- Imported structure builds at project root without app/ wrapper — all folders created directly at
  the project root level
- Tree parser handles `__init__.py` → `create_init: True` conversion, root wrapper stripping,
  deeply nested structures, and both box-drawing and plain indentation formats
- Imported structure state persisted in project history and presets
- `uv.lock` added to UV-generated files skip set to prevent empty lockfile parse errors
- 71 new tests for tree parser, canonical path resolution, and filesystem handler — 776 total

## [0.3.5]

### Changed

- Renamed project and package to uv-forger and uv_forge to sync with PyPi release.

## [0.3.4]

### Changed

- Replaced non-functional "Save to config" checkbox with a Save as Preset button in the Project
  Structure section — opens the Presets dialog for proper, persistent configuration saving
- Button enables automatically when you modify the project configuration (select a
  framework/project type, add packages, or edit the folder structure)
- Added ⌘S / Ctrl+S keyboard shortcut to save as preset

### Removed

- Removed unused save_config() method that wrote to the installed package directory (would be
  wiped on upgrade)
- Removed auto_save_folders state field and on_auto_save_toggle handler (dead code)

## [0.3.3] - 2026-03-18

### Fixed

- Custom dropdown in light mode

## [0.3.2] - 2026-3-16

### Internal

- Fixed image link

## [0.3.1] - 2026-03-15

### Added

- Import existing folder from disk into project template
  - "Import from Disk..." button in Add File/Folder dialog (Folder type)
  - Right-click context menu on folders: "Import Folder from Disk..."
  - Recursive directory scanner with depth (5) and file (50) limits
  - Reads content of importable file types (.py, .json, .toml, .md, .yaml, .html, .css, .js,
  .ts, etc.)
  - Skips hidden dirs, __pycache__, node_modules, .venv, dist, build, and other noise
  - Skips binary/non-UTF-8 files gracefully with skipped count reported
  - Imported file contents stored as overrides and written during build
- Context menu on folders (previously only files had one)

### Changed

- Added httpx to FastAPI project type packages
- Updated FastAPI built-in preset to include httpx and pydantic as runtime deps

### Internal

- Extracted `IMPORTABLE_EXTENSIONS` constant (was duplicated in two places)
- 14 new tests (scanner, context menu, dialog) — 719 total

## [0.3.0] - 2026-03-15

### Added

- Browse button in Add File dialog — import existing files from disk when adding to the folder tree (name auto-fills, content stored for build)
- FCE-enhanced file editor integration with syntax highlighting, search & replace, diff pane, and user templates
- File content editing via right-click context menu on files in the folder tree (Preview, Edit, Import from File, Reset to Default)
- Full-screen code editor powered by fce-enhanced with syntax highlighting, search & replace, diff pane, command palette, and font zoom
- User templates system — save custom boilerplate that persists across sessions and overrides built-in content
- Custom content indicators (✎ pencil icon) in the folder tree for files with overrides
- Edit File toolbar button for quick access to the editor
- Custom Templates Path setting for user-level boilerplate directory
- File overrides applied during build with priority over boilerplate

### Changed

- Boilerplate fallback chain updated to check user templates first
- In-app docs (Help, About, Cheat Sheet) updated to cover file editor features

### Fixed

- FilePicker API corrected from broken `get_file_path()` to `pick_files()` (Flet 0.80+ compatible)

## [0.2.0] - 2026-03-11

### Added

- Configurable git remote mode: Local Bare Repo (default), GitHub (via `gh repo create`), or None (local only)
- GitHub CLI pre-flight checks (`gh` installed and authenticated) before GitHub-mode builds
- Settings for git remote mode, GitHub username/org, and private/public repo visibility
- Per-build git remote mode override in the Confirm Build dialog
- "Check gh status" button in Settings dialog
- GitHub Actions workflow for automatic docs deployment to GitHub Pages

### Changed

- Git integration documentation rewritten across README, HELP, Cheat Sheet, and mkdocs guide pages

## [0.1.0] - 2026-03-10

### Added

- Initial release of UV Forger
- Flet desktop GUI for scaffolding Python projects with UV
- 10 UI framework templates (Flet, PyQt6, PySide6, tkinter, customtkinter, Kivy, Pygame, NiceGUI, Streamlit, Gradio)
- 21 project type templates (Django, FastAPI, Flask, data science, ML, CLI tools, APIs, web scraping, and more)
- JSON-based template system with fallback hierarchy and intelligent merging
- Smart scaffolding with boilerplate file content and `{{project_name}}` placeholder substitution
- PyPI name availability checker with PEP 503 normalization
- Two-phase git integration (local repo + bare hub, auto commit and push)
- Dev dependency support (`uv add --dev`) with amber badge in UI
- Project metadata dialog (author, email, description, SPDX license)
- Post-build automation with configurable shell commands
- Rollback system for cleanup on build failure
- Named project presets with 4 built-in starters
- Recent projects history (last 5 builds)
- Persistent settings (project path, GitHub root, Python version, IDE, git defaults)
- Colour-coded log viewer with clickable source locations
- Dark and light theme toggle

[0.4.0]: https://github.com/oktl/uv-forger/releases/tag/v0.4.0
[0.3.5]: https://github.com/oktl/uv-forger/releases/tag/v0.3.5
[0.3.4]: https://github.com/oktl/uv-forger/releases/tag/v0.3.4
[0.3.3]: https://github.com/oktl/uv-forger/releases/tag/v0.3.3
[0.3.2]: https://github.com/oktl/uv-forger/releases/tag/v0.3.2
[0.3.1]: https://github.com/oktl/uv-forger/releases/tag/v0.3.1
[0.3.0]: https://github.com/oktl/uv-forger/releases/tag/v0.3.0
[0.2.0]: https://github.com/oktl/uv-forger/releases/tag/v0.2.0
[0.1.0]: https://github.com/oktl/uv-forger/releases/tag/v0.1.0
