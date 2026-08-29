# Architecture

This page is a map of the UV Forger codebase for contributors.
It covers module responsibilities, key patterns, and how data flows through the app.

---

## Module Map

### core/

Core logic with no UI dependencies.

| Module                  | Role                                                  |
| ----------------------- | ----------------------------------------------------- |
| **`constants.py`**      | Single source of truth: versions, frameworks, package maps, paths |
| **`state.py`**          | `AppState` — `@ft.observable` dataclass, all mutable state |
| **`models.py`**         | Data models: `FolderSpec`, `ProjectConfig`, `BuildResult`; `get_canonical_file_path()` |
| **`validator.py`**      | Project name, folder name, and path validation        |
| **`template_loader.py`**| JSON template loading with fallback chain             |
| **`template_merger.py`**| Merges framework + project type templates recursively |
| **`boilerplate_resolver.py`** | Populates created files with starter content    |
| **`pypi_checker.py`**   | Async PyPI name availability check (`httpx`, PEP 503) |
| **`async_executor.py`** | `ThreadPoolExecutor` wrapper for subprocess calls     |
| **`settings_manager.py`** | `AppSettings` load/save to platformdirs JSON        |
| **`history_manager.py`**  | Recent projects history (capped at 5)               |
| **`preset_manager.py`**   | Named configuration presets (user + built-in)       |
| **`tree_parser.py`**      | Parse box-drawing and indented text trees into `FolderSpec` structures |
| **`logging_config.py`**   | Loguru setup: console + file handlers with rotation |

### handlers/

Event handling and build orchestration. All handlers receive `(page, controls, state)`.

| Module                   | Role                                                 |
| ------------------------ | ---------------------------------------------------- |
| **`ui_handler.py`**      | `Handlers` class (mixin composition) + `attach_handlers()` wiring |
| **`handler_base.py`**    | `HandlerBase` mixin — shared helpers (snackbar, status, validation) |
| **`input_handlers.py`**  | Path and name input handlers                         |
| **`option_handlers.py`** | Checkboxes, dialogs, template loading/merging        |
| **`folder_handlers.py`** | Folder tree display and management                   |
| **`package_handlers.py`**| Package list display, dev toggles                    |
| **`build_handlers.py`**  | Build, reset, exit, keyboard shortcuts, history restore, preset apply |
| **`feature_handlers.py`**| Theme toggle, help, about, settings, log viewer, history, presets |
| **`project_builder.py`** | `build_project()` orchestration — UV init → git → folders → packages |
| **`filesystem_handler.py`** | Folder creation, `cleanup_on_error()` rollback    |
| **`uv_handler.py`**      | `run_uv_init()`, `install_package()`, `setup_virtual_env()` |
| **`git_handler.py`**     | Two-phase git setup: init → commit/push              |

### ui/

Flet controls, dialogs, and theming.

| Module                | Role                                                    |
| --------------------- | ------------------------------------------------------- |
| **`components.py`**   | `Controls` class + `build_main_view()` — appbar overflow menu |
| **`packages_panel.py`** | `PackagesPanel` — declarative package list (`@ft.component`) |
| **`folders_panel.py`**  | `FoldersPanel` — declarative project structure tree (`@ft.component`) |
| **`dialogs.py`**      | App-specific dialogs: confirm, settings, build summary, history, presets |
| **`content_dialogs.py`** | Reusable content dialogs: help, about, file edit, preview |
| **`dialog_data.py`**  | Framework/project type categories — dialog display metadata |
| **`custom_dropdown.py`** | `CustomDropdown` — animated overlay dropdown (Python version, presets) |
| **`tree_builder.py`** | Project tree builder: plain-text + styled Flet controls |
| **`theme_manager.py`**| `get_theme_colors()` singleton                          |
| **`ui_config.py`**    | UI constants (colours, sizes)                           |

---

## Key Patterns

### Handler Mixin Composition

The `Handlers` class in `ui_handler.py` composes six mixins (`InputHandlers`, `OptionHandlers`, `FolderHandlers`, `PackageHandlers`, `BuildHandlers`, `FeatureHandlers`), all inheriting from `HandlerBase` for shared helpers like `show_snackbar()` and `set_status()`. The standalone `attach_handlers()` function wires handler methods to UI control callbacks.

### Async in Flet

Flet 0.80+ uses sync callbacks, so async coroutines must be wrapped:

```python
def wrap_async(coro_func):
    def wrapper(e):
        asyncio.create_task(coro_func(e))
    return wrapper

controls.some_button.on_click = wrap_async(handler.on_some_click)
```

Use `AsyncExecutor.run()` to offload subprocess calls (UV, git) to a thread pool, keeping the UI responsive. `CustomDropdown` callbacks are an exception — they receive a plain `str` and are wired directly without `wrap_async`.

### Template Loading Chain

Templates load through a 3-step fallback:

1. Framework-specific template (e.g., `ui_frameworks/flet.json`)
2. `ui_frameworks/default.json`
3. Hardcoded `DEFAULT_FOLDERS` in `constants.py`

When both a UI framework and project type are selected, both templates are loaded and merged via `merge_folder_lists()` — folders matched by name are merged recursively, unmatched folders are included from both sides. The single entry point for all template loading is `_reload_and_merge_templates()` in `option_handlers.py`.

### Imported Tree Structures

When a user imports a tree structure (via the Import Tree button), `parse_tree_text_full()` in `tree_parser.py` returns a `TreeParseResult` containing both folders and root-level files. Root files are stored in `state.root_files` (separate from `state.folders`) and use navigation paths like `["root_files", idx]` for selection and editing. `get_canonical_file_path()` in `core/models.py` resolves these paths for the file override system. During build, `setup_imported_structure()` creates folders at the project root (no `app/` wrapper) and writes root files — UV-generated files are only skipped if the user hasn't edited them.

### Declarative Panels in an Imperative App

The packages list and the project structure tree are Flet **components**
(`@ft.component`), rendered from state rather than rebuilt control-by-control. Everything else
— the main view, every dialog — is still imperative, so each panel is rendered on its own
`Renderer()` and dropped into the layout by `render_packages_panel()` / `render_folders_panel()`
in `components.py`.

Mixing the two styles has exactly two rules, and both failure modes are silent:

1. **Pass state as a getter, not as the observable.** Flet subscribes a component to any
   `Observable` argument, whole-object, with no field-level filtering. Passing `AppState`
   directly would mark the panel dirty on every unrelated write (a checkbox, the project name),
   and the next imperative `page.update()` would then re-render it into fresh control ids
   *without* patching the client — after which every click inside the panel is dropped with no
   error. So the panels take `lambda: state`.
2. **`ft.memo` is required, not an optimization.** Same failure mode, triggered by an unrelated
   `page.update()` reaching a clean component.

Because of rule 1 the panels never go dirty on their own, so invalidation stays explicit:
handlers call `controls.packages_panel.update()` / `controls.folders_panel.update()` — the only
path that re-renders *and* patches the client — after `page.update()`. No components mode and no
update scheduler are needed.

Panels are built before handlers exist, so clicks dispatch through slots that
`attach_handlers()` fills in later: `controls.on_package_select` for packages, and a
`FolderPanelCallbacks` dataclass (row select, file menu, folder menu) for the tree.

### Build Pipeline

`build_project()` in `project_builder.py` orchestrates the full build sequence. Total steps are computed dynamically based on config, and an `on_progress` callback drives the determinate progress bar. On failure, `cleanup_on_error()` removes the partial project directory.

```mermaid
flowchart TD
    A[UV init] --> B[Create folders] --> C[Configure pyproject.toml] --> D[Set up venv]
    D --> E{Packages?}
    E -- yes --> F[Install packages] --> G{Git enabled?}
    E -- no --> G
    G -- yes --> H[Git init / commit] --> I{Post-build hook?}
    G -- no --> I
    I -- yes --> J[Run hook] --> K[Done]
    I -- no --> K
```

---

## Data Flow

```mermaid
flowchart TD
    subgraph Startup
        S[main.py] --> State[AppState]
        S --> View[build_main_view]
        View --> Controls[Controls]
    end

    subgraph Runtime
        User([User interaction]) --> Handlers
        Handlers -- "mutate" --> State
        Handlers -- "update" --> Controls
    end

    State --> Handlers
    Controls --> Handlers

    subgraph Build ["Build — on click"]
        Handlers -- "reads state" --> BP[build_project]
        BP --> FS[filesystem_handler]
        BP --> UV[uv_handler]
        BP --> Git[git_handler]
    end
```

`AppState` is created at startup and passed to both `build_main_view()` and `Handlers()`. User interactions trigger handler methods that mutate state and update controls. On build, `build_project()` reads the current state and delegates to the filesystem, UV, and git handlers.

---

## Adding New Features

!!! tip "Contributor checklist"

    - **New framework or project type** — Add to `constants.py`, create a template JSON, add to `dialog_data.py`. See [Adding a new template](../guide/templates.md#adding-a-new-template).
    - **New boilerplate** — Drop a file into `config/templates/boilerplate/` under the right subdirectory. No code changes needed.
    - **New handler** — Add a method to the appropriate mixin, wire it in `attach_handlers()`.
    - **New setting** — Add a field to `AppSettings` in `settings_manager.py`, add a row to the settings dialog in `dialogs.py`.
    - **New dialog** — Add to `dialogs.py` (app-specific) or `content_dialogs.py` (reusable content). Wire via a menu item in `components.py` and a handler in `feature_handlers.py`.
