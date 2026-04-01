# UV Forger

**Version 0.4.0**

A desktop application for creating Python projects with UV — the fast Python package manager. Provides template-based folder structures, framework/package installation, git initialization, and Python version selection.

---

## Tech Stack

| Component                                            | Version  |
| ---------------------------------------------------- | -------- |
| Python                                               | 3.12+    |
| [Flet](https://flet.dev)                             | 0.80.5+  |
| [uv](https://docs.astral.sh/uv/)                     | external |
| [httpx](https://www.python-httpx.org/)               | 0.28+    |
| [loguru](https://loguru.readthedocs.io/)             | 0.7+     |
| [platformdirs](https://platformdirs.readthedocs.io/) | 4.0+     |

**Git** (optional, for repository initialization)

---

## Key Features

- **10 UI Frameworks** — Flet, PyQt6, PySide6, tkinter, customtkinter, Kivy, Pygame, NiceGUI, Streamlit, Gradio
- **21 Project Types** — Django, FastAPI, Flask, data science, web scraping, CLI tools, and more
- **Template Merging** — Select both a UI framework and project type to automatically merge their folder structures
- **Smart Scaffolding** — Starter files populated with boilerplate content instead of empty files
- **PyPI Name Checker** — Verify package name availability before building
- **User Settings** — Configurable defaults for project path, Python version, IDE preference, and git; persisted to disk
- **Git Integration** — Two-phase setup with local repo and bare hub (path configurable via Settings)
- **Async Operations** — UV and git commands run off the UI thread for a responsive experience
- **File Editor** — Preview, edit, and import file content before building with full IDE-like editing via fce-enhanced. Import files from disk directly in the Add File dialog via Browse button
- **User Templates** — Persistent custom boilerplate that overrides built-in templates across sessions
- **Presets** — Save and apply named configurations; ships with 4 built-in starter presets
- **Recent Projects** — Restore settings from your last 5 builds with one click
- **Log Viewer** — Colour-coded log display with clickable source locations that open in your IDE
- **Theme Support** — Toggle between dark and light mode
- **Build Progress** — Determinate progress bar with step counter during builds
- **Import Tree Structure** — Paste a text tree to define a complete project layout with root-level files, editable before build
- **Error Handling** — Rollback and cleanup on build failure

---

## More Information

- [Help & Documentation](app://help) — Usage guide and keyboard shortcuts
- [App Cheat Sheet](app://app-cheat-sheet) — Quick reference for UV Forger features

---

## Credits

Built with [Flet](https://flet.dev) and [UV](https://docs.astral.sh/uv/).

Created by Tim with assistance from Claude Code.
