# UV Forger Cheat Sheet

## Keyboard Shortcuts

| Shortcut | Action                  |
| -------- | ----------------------- |
| `⌘Enter` | Build project           |
| `⌘F`     | Add folder or file      |
| `⌘P`     | Add packages            |
| `⌘S`     | Save as Preset          |
| `⌘R`     | Reset all fields        |
| `⌘/`     | Open Help               |
| `Esc`    | Close dialog / Exit app |

On Windows/Linux, replace ⌘ with Ctrl.

---

## Quick Build Checklist

1. Enter a **project name** (valid Python package name)
2. Set **project path** (default from Settings)
3. Pick **Python version** (default: 3.14)
4. Optionally enable **Git**, **UI framework**, **project type**
5. `⌘Enter` → review confirm dialog → **Build**

---

## Build Pipeline

A **progress bar** with step counter (e.g., "3/7") tracks each stage. Steps are conditional — git-disabled builds skip git steps, no-packages builds skip install. Total varies from 5 to 7 steps.

| Step | What happens                                       | Condition          |
| ---- | -------------------------------------------------- | ------------------ |
| 1    | `uv init` — scaffolds pyproject.toml               | always             |
| 2    | Git Phase 1 — local repo (+ bare hub if Local mode) | git enabled        |
| 3    | Create folder structure from templates              | always             |
| 4    | Configure pyproject.toml (metadata, authors, etc.) | always             |
| 5    | `uv venv` — create virtual environment             | always             |
| 6    | `uv add` — install packages (+ `--dev` for dev)    | packages > 0       |
| 7    | Git Phase 2 — stage, commit, push (mode-dependent) | git enabled        |
| —    | Run post-build command (if enabled)                | after build        |

---

## Template Merging (Framework + Project Type)

| Scenario          | Result                                                            |
| ----------------- | ----------------------------------------------------------------- |
| Framework only    | Framework template (fallback → default → hardcoded)               |
| Project type only | Project type template loaded                                      |
| Both selected     | Merged — matching folders combined, unique folders kept from both |
| Neither           | Default template structure                                        |

**Merge rules:** folders matched by name → subfolders merged recursively, files unioned, booleans OR'd.

---

## Smart Scaffolding (Boilerplate)

Files get starter content instead of being empty. Fallback chain:

1. **User templates** — persistent custom content (saved via editor)
2. `boilerplate/ui_frameworks/{framework}/{file}` — framework-specific
3. `boilerplate/project_types/{type}/{file}` — project-type-specific
4. `boilerplate/common/{file}` — shared utilities
5. Empty file — if no boilerplate found

`{{project_name}}` in templates → replaced with title case (e.g., `my_app` → `My App`).

---

## File & Folder Content Editing

Right-click a file in the folder tree for a context menu:

| Action | What it does |
| --- | --- |
| Preview Content | Read-only view of boilerplate or custom content |
| Edit Content... | Full-screen code editor (fce-enhanced) |
| Import from File... | Load content from a file on disk |
| Browse... (Add File dialog) | Import existing file content when adding a new file |
| Reset to Default | Remove overrides, revert to boilerplate |

Right-click a folder in the folder tree:

| Action | What it does |
| --- | --- |
| Import Folder from Disk... | Pick a directory and import it as a subfolder with all its contents |

Import an existing folder via the Add Folder/File dialog:

| Action | What it does |
| --- | --- |
| Import from Disk... (Add Folder dialog) | Pick a directory — its structure and file contents are scanned and added |

Folder import scans up to 5 levels deep and 50 files. Skips hidden dirs, `.git`, `__pycache__`, `node_modules`, `.venv`, and binary files. A summary shows folders/files/skipped counts.

**Import Tree Structure** — paste a text tree to define a complete project layout:

| Action | What it does |
| --- | --- |
| Import Tree (button) | Paste a box-drawing or indented text tree to define project structure |
| Preview | Parse and show folder/file/root-file counts before importing |
| Replace mode | Replace current folder structure entirely |
| Merge mode | Combine imported structure with existing folders |

Root-level files (e.g., LICENSE, CHANGELOG.md) appear in the main display and can be edited. UV-generated files (pyproject.toml, README.md, etc.) can be overridden with custom content. `__init__.py` entries auto-convert to `create_init` flags.

Files with custom content show a **✎** pencil indicator.

**Editor shortcuts:**

| Shortcut | Action |
| --- | --- |
| `⌘F` | Search |
| `⌘⌥F` | Search & Replace |
| `⌘S` | Save to user templates |
| `⌘⇧S` | Save As |
| `⌘D` | Toggle diff pane |
| `⌘G` | Go to line |
| `⌘L` | Toggle read-only |
| `⌘⇧P` | Command palette |
| `⌘±` | Zoom font size |
| `Esc` | Close search / close editor |

On Windows/Linux, replace ⌘ with Ctrl and ⌥ with Alt.

---

## PyPI Name Check

Click the globe icon next to the project name field:

| Colour | Meaning                         |
| ------ | ------------------------------- |
| Green  | Name available on PyPI          |
| Red    | Name taken (PEP 503 normalized) |
| Orange | Could not reach PyPI            |

Names are normalized: `my_app` = `my-app` = `my.app`.

---

## Packages

| Action          | How                                                     |
| --------------- | ------------------------------------------------------- |
| Add packages    | `⌘P` → type name → Enter                                |
| Mark as dev     | Select package → "Toggle Dev" (or checkbox when adding) |
| Clear all       | "Clear Packages" button (confirms first)                |
| PyPI validation | Each package checked live in the Add dialog             |

Dev packages install with `uv add --dev` → `[dependency-groups]` in pyproject.toml. Shown with an amber "dev" badge.

---

## Settings Quick Reference

| Setting              | What it does                                 |
| -------------------- | -------------------------------------------- |
| Default Project Path | Where new projects are created               |
| GitHub Root          | Location for bare hub repositories           |
| Python Version       | Default version for new projects             |
| Preferred IDE        | IDE for "Open in IDE" post-build action      |
| Git Default          | Whether Git checkbox is pre-checked          |
| Author Name/Email    | Default project metadata                     |
| Git Remote Mode      | Local Bare Repo / GitHub / None (local only) |
| GitHub Username      | Username or org for GitHub repo creation      |
| Private Repos        | Whether GitHub repos are created as private   |
| Custom Templates Path| Directory for user-level boilerplate templates|
| Post-build Command   | Shell command run after successful builds     |
| Post-build Packages  | Packages auto-installed when command enabled  |

Settings stored in `~/Library/Application Support/UV Forger/settings.json` (macOS), `%LOCALAPPDATA%\UV Forger\settings.json` (Windows), or `~/.local/share/UV Forger/settings.json` (Linux).

---

## Presets vs Recent Projects

| Feature   | Presets                    | Recent Projects        |
| --------- | -------------------------- | ---------------------- |
| Purpose   | Reusable project templates | History of past builds |
| Limit     | Unlimited (user presets)   | Last 5 builds          |
| Built-ins | 4 starter presets included | None                   |
| Saves     | Config only (no name/path) | Full build snapshot    |
| On apply  | Keeps current name & path  | Restores everything    |
| Storage   | `presets.json`             | `recent_projects.json` |

**Built-in presets:** Flet Desktop App, FastAPI Backend, Data Science Starter, CLI Tool (Typer). Shown with a teal "Built-in" badge; cannot be deleted.

---

## Post-Build Command

Configure in Settings → runs after every successful build.

- Command runs in the new project directory with `shell=True`
- 30-second timeout
- Required packages (comma-separated) auto-installed during build
- Override per-build in the confirm dialog

Example: `uv run pre-commit install && uv run pytest`

---

## Git Two-Phase Setup

Behaviour depends on the **Git Remote Mode** setting:

| Mode              | Phase 1                                      | Phase 2                                          |
| ----------------- | -------------------------------------------- | ------------------------------------------------ |
| Local Bare Repo   | `git init` + bare hub + `remote add origin`  | `git add .` + commit + `push -u origin HEAD`     |
| GitHub            | `git init` only                              | `git add .` + commit + `gh repo create` + push   |
| None (local only) | `git init` only                              | `git add .` + commit (no push)                   |

Hub path configurable in Settings → GitHub Root. GitHub mode requires the `gh` CLI.

---

## See Also

- [Help & Documentation](app://help) — Full usage guide
- [About UV Forger](app://about) — App info and tech stack
