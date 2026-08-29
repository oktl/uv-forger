"""Application constants and default values.

This module centralizes all constant values used throughout the application,
including Python version options, UI frameworks, and default paths.
"""

from pathlib import Path

import platformdirs

APP_VERSION = "0.5.0"

# Python versions supported by the application
PYTHON_VERSIONS = ["3.14", "3.13", "3.12", "3.11", "3.10"]
DEFAULT_PYTHON_VERSION = "3.14"

# UI frameworks available for project creation
UI_FRAMEWORKS = [
    "flet",
    "PyQt6",
    "PySide6",
    "tkinter (built-in)",
    "customtkinter",
    "kivy",
    "pygame",
    "nicegui",
    "streamlit",
    "gradio",
]
DEFAULT_FRAMEWORK = "flet"

# Framework package name mappings (for uv add)
FRAMEWORK_PACKAGE_MAP = {
    "flet": "flet",
    "PyQt6": "pyqt6",
    "PySide6": "pyside6",
    "customtkinter": "customtkinter",
    "kivy": "kivy",
    "pygame": "pygame",
    "nicegui": "nicegui",
    "streamlit": "streamlit",
    "gradio": "gradio",
    "tkinter (built-in)": None,  # Built-in, no installation needed
}

# Project type package mappings (for uv add)
# Maps project type to list of required packages
# Packages that should always be marked as dev dependencies
ALWAYS_DEV_PACKAGES = {"pre-commit", "pytest", "pytest-cov", "pytest-mock", "ruff"}

PROJECT_TYPE_PACKAGE_MAP = {
    # Web Frameworks
    "django": ["django"],
    "fastapi": ["fastapi", "uvicorn"],
    "flask": ["flask"],
    "bottle": ["bottle"],
    # Data Science & ML
    "data_analysis": ["pandas", "numpy", "matplotlib", "jupyter"],
    "ml_sklearn": ["scikit-learn", "pandas", "numpy", "matplotlib"],
    "dl_pytorch": ["torch", "torchvision", "numpy"],
    "dl_tensorflow": ["tensorflow", "numpy"],
    "computer_vision": ["opencv-python", "numpy", "pillow"],
    # CLI Tools
    "cli_click": ["click"],
    "cli_typer": ["typer[all]"],
    "cli_rich": ["rich"],
    # API Development
    "api_fastapi": ["fastapi", "uvicorn", "httpx", "pydantic"],
    "api_graphql": ["strawberry-graphql[fastapi]"],
    "api_grpc": ["grpcio", "grpcio-tools", "protobuf"],
    # Automation & Scraping
    "browser_automation": ["playwright"],
    "task_scheduler": ["apscheduler"],
    "scraping": ["beautifulsoup4", "httpx", "lxml"],
    # Other
    "basic_package": [],  # No packages needed
    "testing": ["pytest", "pytest-cov", "pytest-mock"],
    "async_app": ["aiohttp", "aiofiles"],
}

# Framework entry point mappings (None = no [project.scripts] section)
FRAMEWORK_ENTRY_POINT_MAP = {
    "flet": "app.main:run",
    "PyQt6": "app.main:run",
    "PySide6": "app.main:run",
    "tkinter (built-in)": "app.main:run",
    "customtkinter": "app.main:run",
    "kivy": "app.main:run",
    "pygame": "app.main:run",
    "nicegui": "app.main:run",
    "streamlit": None,  # Uses `streamlit run`
    "gradio": None,  # Uses `gradio` or `python` directly
}

# Project type entry point mappings (None = no [project.scripts] section)
PROJECT_TYPE_ENTRY_POINT_MAP = {
    # Web frameworks — have their own runners
    "django": None,
    "fastapi": None,
    "flask": None,
    "bottle": None,
    # API types — have their own runners
    "api_fastapi": None,
    "api_graphql": None,
    "api_grpc": None,
    # CLI tools — specific entry points
    "cli_click": "app.main:cli",
    "cli_typer": "app.main:app",
    "cli_rich": "app.main:main",
    # Everything else → standard main
    "data_analysis": "app.main:main",
    "ml_sklearn": "app.main:main",
    "dl_pytorch": "app.main:main",
    "dl_tensorflow": "app.main:main",
    "computer_vision": "app.main:main",
    "browser_automation": "app.main:main",
    "task_scheduler": "app.main:main",
    "scraping": "app.main:main",
    "basic_package": "app.main:main",
    "testing": "app.main:main",
    "async_app": "app.main:main",
}

# Default entry point when no framework or project type is selected
DEFAULT_ENTRY_POINT = "app.main:main"

# Configuration paths
LOG_DIR = Path(platformdirs.user_data_dir("UV Forger")) / "logs"
TEMPLATES_DIR = Path(__file__).parent.parent / "config" / "templates"
UI_TEMPLATES_DIR = TEMPLATES_DIR / "ui_frameworks"
PROJECT_TYPE_TEMPLATES_DIR = TEMPLATES_DIR / "project_types"
BOILERPLATE_DIR = TEMPLATES_DIR / "boilerplate"
DOCS_DIR = Path(__file__).parent.parent / "assets" / "docs"
HELP_FILE = DOCS_DIR / "HELP.md"
APP_CHEAT_SHEET_FILE = DOCS_DIR / "App-Cheat-Sheet.md"
ABOUT_FILE = DOCS_DIR / "ABOUT.md"

# Default paths
DEFAULT_PROJECT_ROOT = Path.home() / "Projects"
DEFAULT_GIT_HUB_ROOT = Path.home() / "Projects" / "git-repos"

# Supported IDEs — display name → CLI command (None = user provides path)
SUPPORTED_IDES: dict[str, str | None] = {
    "VS Code": "code",
    "PyCharm": "pycharm",
    "Zed": "zed",
    "Cursor": "cursor",
    "Other / Custom": None,
}

# macOS app names for IDEs that need `open -a` on darwin
IDE_MACOS_APP_NAMES: dict[str, str] = {
    "VS Code": "Visual Studio Code",
    "Cursor": "Cursor",
    "Zed": "Zed",
    "PyCharm": "PyCharm",
}

# Git remote modes
GIT_REMOTE_MODES = ("local", "github", "none")
GIT_REMOTE_MODE_LABELS = {
    "local": "Local Bare Repo",
    "github": "GitHub",
    "none": "None (local only)",
}

# License types for project metadata (SPDX identifiers)
LICENSE_TYPES = [
    "MIT",
    "Apache-2.0",
    "GPL-3.0",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "ISC",
    "MPL-2.0",
    "LGPL-3.0",
    "Unlicense",
]

# Default folder structure (used as final fallback)
DEFAULT_FOLDERS = ["core", "ui", "utils", "assets"]
