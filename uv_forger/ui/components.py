"""UI components and layout construction for the Project Creator.

This module defines the Controls class for storing UI control references and
the build_main_view function for constructing the application's visual layout.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft
from flet.components.component import Renderer

from uv_forger.core.constants import PYTHON_VERSIONS
from uv_forger.core.preset_manager import load_presets
from uv_forger.ui.custom_dropdown import CustomDropdown
from uv_forger.ui.packages_panel import PackagesPanel
from uv_forger.ui.theme_manager import get_theme_colors
from uv_forger.ui.ui_config import UIConfig

if TYPE_CHECKING:
    from uv_forger.core.state import AppState


class Controls:
    """Container for reference to controls.

    Stores references to interactive UI elements for access by event handlers.

    Attributes:
        project_path_label: Label for project path input.
        project_path_input: TextField for entering project path.
        copy_path_button: IconButton to copy the full project path to clipboard.
        browse_button: Button to open directory picker.
        warning_banner: Text for displaying warnings.
        project_name_label: Label for project name input.
        project_name_input: TextField for entering project name.
        python_version_label: Label for Python version dropdown.
        python_version_dropdown: Dropdown for selecting Python version.
        create_git_checkbox: Checkbox for git initialization option.
        ui_project_checkbox: Checkbox for UI project option.
        other_projects_checkbox: Checkbox for Other Project types option.
        app_subfolders_label: Label for folder display.
        subfolders_container: Container showing folder structure.
        save_as_preset_button: Button to save current config as a preset.
        add_folder_button: Button to add a folder.
        remove_folder_button: Button to remove a folder.
        edit_file_button: Button to edit a file's content.
        packages_label: Label for packages display.
        packages_panel: PackagesPanel component rendering the package list.
        on_package_select: Callback invoked with the clicked package index;
            wired by attach_handlers().
        add_package_button: Button to open the add-packages dialog.
        remove_package_button: Button to remove the selected package.
        clear_packages_button: Button to remove all packages from the list.
        toggle_dev_button: Button to toggle selected package between runtime and dev dependency.
        include_starter_files_checkbox: Checkbox to include starter files in template.
        path_preview_text: Small greyed text showing the resolved project path as the user types.
        status_icon: Icon to indicate status (info, warning, error).
        status_text: Text for displaying status messages.
        build_project_button: Button to build the project.
        reset_button: Button to reset all fields.
        exit_button: Button to exit the application.
        progress_ring: Progress indicator for async operations.
        progress_bar: Progress bar for multi-step operations.
        progress_step_text: Text to show current step in multi-step operations.
        about_menu_item: Menu item to show about dialog.
        help_menu_item: Menu item to show help dialog.
        app_cheat_sheet_menu_item: Menu item to show app cheat sheet dialog.
        settings_menu_item: Menu item to show settings dialog.
        history_menu_item: Menu item to show recent projects dialog.
        presets_menu_item: Menu item to show presets management dialog.
        log_viewer_menu_item: Menu item to show log viewer dialog.
        overflow_menu: PopupMenuButton containing infrequent actions.
        theme_toggle_button: Button to toggle theme.
        pypi_status_text: Text to show PyPI name availability status.
        metadata_checkbox: Checkbox to enable project metadata input.
        metadata_summary: Text to show a summary of the entered metadata.
        main_title: Main title text.
        section_titles: List of section title texts.
        section_containers: List of section containers.
    """

    def __init__(self) -> None:
        self.project_path_label: ft.Text
        self.project_path_input: ft.TextField
        self.copy_path_button: ft.IconButton
        self.browse_button: ft.Button
        self.warning_banner: ft.Text
        self.project_name_label: ft.Text
        self.project_name_input: ft.TextField
        self.python_version_label: ft.Text
        self.python_version_dropdown: ft.Dropdown
        self.create_git_checkbox: ft.Checkbox
        self.ui_project_checkbox: ft.Checkbox
        self.other_projects_checkbox: ft.Checkbox
        self.app_subfolders_label: ft.Text
        self.subfolders_container: ft.Container
        self.save_as_preset_button: ft.Button
        self.add_folder_button: ft.Button
        self.remove_folder_button: ft.Button
        self.edit_file_button: ft.Button
        self.import_tree_button: ft.Button
        self.clear_folders_button: ft.Button
        self.packages_label: ft.Text
        self.packages_panel: ft.Control
        self.on_package_select: Callable[[int], None] | None = None
        self.add_package_button: ft.Button
        self.remove_package_button: ft.Button
        self.clear_packages_button: ft.Button
        self.toggle_dev_button: ft.Button
        self.include_starter_files_checkbox: ft.Checkbox
        self.path_preview_text: ft.Text
        self.status_icon: ft.Icon
        self.status_text: ft.Text
        self.build_project_button: ft.Button
        self.reset_button: ft.Button
        self.exit_button: ft.Button
        self.progress_ring: ft.ProgressRing
        self.progress_bar: ft.ProgressBar
        self.progress_step_text: ft.Text
        self.about_menu_item: ft.PopupMenuItem
        self.help_menu_item: ft.PopupMenuItem
        self.app_cheat_sheet_menu_item: ft.PopupMenuItem
        self.settings_menu_item: ft.PopupMenuItem
        self.history_menu_item: ft.PopupMenuItem
        self.presets_menu_item: ft.PopupMenuItem
        self.log_viewer_menu_item: ft.PopupMenuItem
        self.overflow_menu: ft.PopupMenuButton
        self.theme_toggle_button: ft.IconButton
        self.main_title: ft.Text
        self.check_pypi_button: ft.IconButton
        self.pypi_status_text: ft.Text
        self.metadata_checkbox: ft.Checkbox
        self.metadata_summary: ft.Text
        self.section_titles: list[ft.Text]
        self.section_containers: list[ft.Container]


def create_section_box(
    title: str,
    content: list[ft.Control],
    is_dark: bool = False,
    width: int = UIConfig.SECTION_WIDTH,
) -> tuple[ft.Container, ft.Text]:
    """Create a bordered section with a title and content.

    Args:
        title: Section heading text.
        content: List of Flet controls to display inside the section.
        is_dark: Whether dark mode is active (default False).
        width: Width of the section container (default SECTION_WIDTH).

    Returns:
        Tuple of (container, title_text) for theme update access.
    """
    colors = get_theme_colors(is_dark)
    title_text = ft.Text(
        title,
        size=UIConfig.SECTION_TITLE_SIZE,
        weight=ft.FontWeight.W_600,
        color=colors["section_title"],
    )
    container = ft.Container(
        content=ft.Column(
            controls=[
                title_text,
                *content,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=UIConfig.SPACING_SMALL,
        ),
        border=ft.Border.all(UIConfig.BORDER_WIDTH_THIN, colors["section_border"]),
        border_radius=UIConfig.BORDER_RADIUS_DEFAULT,
        padding=UIConfig.PADDING_SECTION,
        width=width,
    )
    return container, title_text


def create_controls(state: AppState, colors: dict) -> Controls:
    """Create all UI controls for the application.

    Args:
        state: The application state instance.
        colors: Theme colors dictionary.

    Returns:
        Controls instance with all UI elements initialized.
    """
    controls = Controls()

    # Icon buttons
    controls.theme_toggle_button = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE if state.is_dark_mode else ft.Icons.DARK_MODE,
        icon_size=UIConfig.ICON_SIZE_DEFAULT,
        tooltip="Toggle dark/light mode",
    )

    # Overflow menu items
    controls.history_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.HISTORY,
        content=ft.Text("Recent Projects"),
    )
    controls.presets_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.BOOKMARK_OUTLINE,
        content=ft.Text("Presets"),
    )
    controls.settings_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.SETTINGS,
        content=ft.Text("Settings"),
    )
    controls.help_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.HELP_OUTLINE,
        content=ft.Text("Help & Documentation"),
    )
    controls.app_cheat_sheet_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.ROCKET_LAUNCH,
        content=ft.Text("App Cheat Sheet"),
    )
    controls.log_viewer_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.ARTICLE,
        content=ft.Text("View Logs"),
    )
    controls.about_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.INFO_OUTLINE,
        content=ft.Text("About"),
    )

    controls.overflow_menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        icon_size=UIConfig.ICON_SIZE_DEFAULT,
        tooltip="More options",
        items=[
            controls.history_menu_item,
            controls.presets_menu_item,
            controls.settings_menu_item,
            ft.PopupMenuItem(),  # Divider
            controls.help_menu_item,
            controls.app_cheat_sheet_menu_item,
            controls.log_viewer_menu_item,
            ft.PopupMenuItem(),  # Divider
            controls.about_menu_item,
        ],
    )

    # Project path controls
    controls.project_path_label = ft.Text("Create Project In")
    controls.project_path_input = ft.TextField(
        value=state.project_path,
        hint_text="Project Root Directory",
        expand=True,
        focused_border_color=ft.Colors.TRANSPARENT,
    )

    controls.copy_path_button = ft.IconButton(
        icon=ft.Icons.CONTENT_COPY,
        icon_size=UIConfig.ICON_SIZE_DEFAULT,
        tooltip="Copy full project path to clipboard",
        disabled=True,
        opacity=0.4,
    )

    controls.browse_button = ft.Button(
        "Browse...",
        tooltip="Browse for project location",
    )

    controls.warning_banner = ft.Text(
        "",
        color=UIConfig.COLOR_WARNING,
        weight=ft.FontWeight.BOLD,
        size=14,
    )

    # Project name controls
    controls.project_name_label = ft.Text("New Project Name")

    controls.project_name_input = ft.TextField(
        hint_text="Enter project name...",
        expand=True,
        autofocus=True,
        border_color=UIConfig.COLOR_INFO,
        border_width=1,
    )

    controls.check_pypi_button = ft.IconButton(
        icon=ft.Icons.TRAVEL_EXPLORE,
        tooltip="Check name availability on PyPI",
        disabled=True,
        icon_size=UIConfig.ICON_SIZE_DEFAULT,
    )

    controls.pypi_status_text = ft.Text(
        "",
        size=UIConfig.TEXT_SIZE_SMALL,
        italic=True,
    )

    controls.path_preview_text = ft.Text(
        "\u00a0",
        size=12,
        color=ft.Colors.GREY_500,
        italic=True,
    )

    # Python version controls
    controls.python_version_label = ft.Text("Python Version")
    controls.python_version_dropdown = CustomDropdown(
        default_value=state.python_version,
        options=list(PYTHON_VERSIONS),
        max_visible=len(PYTHON_VERSIONS),
        width=140,
        height=32,
        tooltip="Python version for this project (set default in Settings)",
    )

    # Preset quick-select
    preset_names = [p.name for p in load_presets()]
    controls.preset_label = ft.Text("Preset")
    controls.preset_dropdown = CustomDropdown(
        default_value="None",
        options=preset_names,
        max_visible=min(len(preset_names), 6),
        width=200,
        height=32,
        tooltip="Apply a saved preset to populate all options",
    )

    # Checkbox controls
    controls.create_git_checkbox = ft.Checkbox(
        label="Initialize Git Repository",
        value=state.git_enabled,
        tooltip="Create a local Git repo with a bare hub for easy pushing",
    )

    controls.include_starter_files_checkbox = ft.Checkbox(
        label="Include Starter Files",
        value=state.include_starter_files,
        label_style=ft.TextStyle(color=UIConfig.COLOR_CHECKBOX_ACTIVE)
        if state.include_starter_files
        else None,
        tooltip="Populate files with starter code instead of creating empty files",
    )

    controls.ui_project_checkbox = ft.Checkbox(
        label="Create UI Project",
        value=state.ui_project_enabled,
        tooltip="Select a UI framework (Flet, PyQt6, Streamlit, etc.)\nCan be combined with Project Type",
    )
    controls.other_projects_checkbox = ft.Checkbox(
        label="Create Other Project Type",
        tooltip="Select a project template (Django, FastAPI, CLI, etc.)\nCan be combined with UI Framework",
    )

    # Folder management controls
    controls.app_subfolders_label = ft.Text("App Subfolders:")
    controls.subfolders_container = ft.Container(
        content=ft.Column(
            controls=[],  # Populated dynamically from template data
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        ),
        border=ft.Border.all(1, ft.Colors.GREY_700),
        border_radius=4,
        padding=10,
        height=UIConfig.SUBFOLDERS_HEIGHT,
        width=UIConfig.SPLIT_CONTAINER_WIDTH,
    )

    _split_btn_style = ft.ButtonStyle(
        text_style=ft.TextStyle(size=UIConfig.TEXT_SIZE_SMALL)
    )

    controls.add_folder_button = ft.Button(
        "Add Folder/File",
        tooltip="Add a folder or file to the project structure\n\n⌘F / Ctrl+F",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    controls.remove_folder_button = ft.Button(
        "Remove Folder/File",
        tooltip="Select an item in the list, then click to remove it",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    controls.save_as_preset_button = ft.Button(
        "Save as Preset",
        icon=ft.Icons.SAVE,
        tooltip="Save the current project configuration as a reusable preset\n\n⌘S / Ctrl+S",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
        disabled=True,
    )

    controls.edit_file_button = ft.Button(
        "Edit File",
        icon=ft.Icons.EDIT,
        tooltip="Edit the content of the selected file\n(or right-click a file in the tree)",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
        disabled=True,
    )

    controls.import_tree_button = ft.Button(
        "Import Tree...",
        icon=ft.Icons.ACCOUNT_TREE,
        tooltip="Paste a text tree structure to populate folders\n\n⌘T / Ctrl+T",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    controls.clear_folders_button = ft.Button(
        "Clear Folders",
        icon=ft.Icons.DELETE_SWEEP,
        tooltip="Remove all folders from the subfolders display",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    # Package management controls
    controls.packages_label = ft.Text("Packages: 0")

    controls.packages_panel = render_packages_panel(state, controls)

    controls.add_package_button = ft.Button(
        "Add Packages...",
        tooltip="Open dialog to add one or more packages to the install list.\n\n⌘P / Ctrl+P",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    controls.remove_package_button = ft.Button(
        "Remove Package",
        tooltip="Select a package in the list, then click to remove it",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    controls.clear_packages_button = ft.Button(
        "Clear Packages",
        tooltip="Remove all packages from the install list.",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    controls.toggle_dev_button = ft.Button(
        "Toggle Dev",
        tooltip="Toggle selected package between runtime and dev dependency.",
        style=_split_btn_style,
        width=UIConfig.BUTTON_WIDTH_STRUCTURE,
    )

    # Metadata controls
    controls.metadata_checkbox = ft.Checkbox(
        label="Set Project Metadata...",
        value=False,
        tooltip="Set author, description, and license for pyproject.toml",
    )
    controls.metadata_summary = ft.Text(
        "",
        size=UIConfig.TEXT_SIZE_SMALL,
        italic=True,
        color=ft.Colors.GREY_500,
    )

    # Status and action controls
    controls.status_icon = ft.Icon(ft.Icons.INFO_OUTLINE, size=16, visible=False)
    controls.status_text = ft.Text("")

    controls.build_project_button = ft.Button(
        content="Build Project",
        tooltip="Create the project with all configured settings\n⌘Enter / Ctrl+Enter",
        bgcolor=UIConfig.COLOR_BTN_BUILD,
        color=ft.Colors.WHITE,
        width=UIConfig.BUTTON_WIDTH_BUILD,
        disabled=True,
        opacity=0.5,
    )

    controls.reset_button = ft.Button(
        content="Reset",
        icon=ft.Icons.REFRESH,
        tooltip="Reset all fields to defaults\n\n⌘R / Ctrl+R",
        bgcolor=UIConfig.COLOR_BTN_RESET,
        color=ft.Colors.WHITE,
        width=UIConfig.BUTTON_WIDTH_ACTION,
    )

    controls.exit_button = ft.Button(
        content="Exit",
        icon=ft.Icons.EXIT_TO_APP,
        tooltip="Exit the application.\n\nEsc",
        bgcolor=UIConfig.COLOR_BTN_EXIT,
        color=ft.Colors.WHITE,
        width=UIConfig.BUTTON_WIDTH_ACTION,
    )

    controls.progress_ring = ft.ProgressRing(
        visible=False,
        width=UIConfig.PROGRESS_RING_SIZE,
        height=UIConfig.PROGRESS_RING_SIZE,
        stroke_width=UIConfig.PROGRESS_RING_STROKE_WIDTH,
    )

    controls.progress_bar = ft.ProgressBar(
        visible=False,
        width=UIConfig.PROGRESS_BAR_WIDTH,
        value=0,
    )
    controls.progress_step_text = ft.Text(
        visible=False,
        size=UIConfig.TEXT_SIZE_SMALL,
        color=UIConfig.COLOR_INFO,
    )

    # Title and container lists
    controls.main_title = ft.Text(
        "UV Forger",
        size=UIConfig.MAIN_TITLE_SIZE,
        weight=ft.FontWeight.BOLD,
        color=colors["main_title"],
    )

    controls.section_titles = []
    controls.section_containers = []

    return controls


def create_sections(controls: Controls, state: AppState) -> None:
    """Create section containers and organize controls into sections.

    Args:
        controls: Controls instance containing all UI elements.
        state: The application state instance.
    """
    # Project path and name section
    project_name_container, project_name_title = create_section_box(
        "Set Project Path and Name",
        [
            ft.Column(
                controls=[
                    controls.project_name_label,
                    ft.Row(
                        controls=[
                            controls.project_name_input,
                            controls.check_pypi_button,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    controls.pypi_status_text,
                    controls.path_preview_text,
                    controls.warning_banner,
                    controls.project_path_label,
                    ft.Row(
                        controls=[
                            controls.project_path_input,
                            controls.copy_path_button,
                            controls.browse_button,
                        ],
                    ),
                ],
            ),
        ],
        state.is_dark_mode,
        width=UIConfig.LEFT_SECTION_WIDTH,
    )
    controls.section_containers.append(project_name_container)
    controls.section_titles.append(project_name_title)

    # Options section
    options_container, options_title = create_section_box(
        "Set Options",
        [
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            controls.python_version_label,
                            controls.python_version_dropdown,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            controls.preset_label,
                            controls.preset_dropdown,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    controls.ui_project_checkbox,
                                    controls.other_projects_checkbox,
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            controls.create_git_checkbox,
                                            ft.Icon(
                                                ft.Icons.INFO_OUTLINE,
                                                size=12,
                                                color=UIConfig.COLOR_INFO,
                                                tooltip=(
                                                    "Creates a local Git repo and  GitHub or local\n bare hub repository.\n"
                                                    "The local hub acts as a local remote origin \nyou can push to.\n"
                                                    "Hub location is configurable in Settings."
                                                ),
                                            ),
                                        ],
                                        spacing=4,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Row(
                                        controls=[
                                            controls.include_starter_files_checkbox,
                                            ft.Icon(
                                                ft.Icons.INFO_OUTLINE,
                                                size=12,
                                                color=UIConfig.COLOR_INFO,
                                                tooltip=(
                                                    "Populates project files with working starter code\n"
                                                    "instead of creating empty files.\n"
                                                    "Available for Flet and other frameworks."
                                                ),
                                            ),
                                        ],
                                        spacing=4,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Row(
                                        controls=[
                                            controls.metadata_checkbox,
                                            controls.metadata_summary,
                                        ],
                                        spacing=8,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                        ],
                        spacing=UIConfig.SPACING_LARGE,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
            ),
        ],
        state.is_dark_mode,
        width=UIConfig.LEFT_SECTION_WIDTH,
    )
    controls.section_containers.append(options_container)
    controls.section_titles.append(options_title)

    # Folders + Packages section (side by side)
    folders_container, folders_title = create_section_box(
        "Project Structure",
        [
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            controls.app_subfolders_label,
                            controls.subfolders_container,
                            ft.Row(
                                controls=[
                                    controls.add_folder_button,
                                    controls.remove_folder_button,
                                ],
                            ),
                            ft.Row(
                                controls=[
                                    controls.edit_file_button,
                                    controls.save_as_preset_button,
                                ],
                            ),
                            ft.Row(
                                controls=[
                                    controls.import_tree_button,
                                    controls.clear_folders_button,
                                ],
                            ),
                        ],
                        spacing=UIConfig.SPACING_SMALL,
                    ),
                    ft.Container(
                        content=ft.VerticalDivider(
                            width=UIConfig.BORDER_WIDTH_DEFAULT,
                            color=ft.Colors.GREY_700,
                        ),
                        height=UIConfig.STRUCTURE_DIVIDER_HEIGHT,
                    ),
                    ft.Column(
                        controls=[
                            controls.packages_label,
                            controls.packages_panel,
                            ft.Row(
                                controls=[
                                    controls.add_package_button,
                                    controls.remove_package_button,
                                ],
                            ),
                            ft.Row(
                                controls=[
                                    controls.clear_packages_button,
                                    controls.toggle_dev_button,
                                ],
                            ),
                        ],
                        spacing=UIConfig.SPACING_SMALL,
                    ),
                ],
                spacing=UIConfig.SPACING_LARGE,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        state.is_dark_mode,
    )
    controls.section_containers.append(folders_container)
    controls.section_titles.append(folders_title)


def create_app_bars(page: ft.Page, controls: Controls, colors: dict) -> None:
    """Create and configure the app bar and bottom app bar.

    Args:
        page: The Flet page to attach app bars to.
        controls: Controls instance containing UI elements.
        colors: Theme colors dictionary.
    """
    page.appbar = ft.AppBar(
        title=ft.Text(
            "Forge a new project with uv",
            size=UIConfig.APPBAR_TITLE_SIZE,
            color=colors["main_title"],
        ),
        bgcolor=ft.Colors.TRANSPARENT,
        actions=[
            controls.theme_toggle_button,
            controls.overflow_menu,
        ],
        toolbar_height=UIConfig.APPBAR_TOOLBAR_HEIGHT,
    )

    page.bottom_appbar = ft.BottomAppBar(
        bgcolor=colors["bottom_bar"],
        content=ft.Row(
            controls=[
                controls.reset_button,
                controls.exit_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=UIConfig.SPACING_XLARGE,
        ),
    )


def create_layout(controls: Controls) -> ft.Column:
    """Create the main layout column with all sections.

    Args:
        controls: Controls instance containing UI elements.

    Returns:
        The root Column control containing the complete UI layout.
    """
    left_column = ft.Column(
        controls=[
            controls.section_containers[0],  # Set Project Path and Name
            controls.section_containers[1],  # Set Options
        ],
        spacing=UIConfig.SPACING_SMALL,
        alignment=ft.MainAxisAlignment.START,
    )

    return ft.Column(
        controls=[
            ft.Image(src="images/badge.png", width=60),
            ft.Container(height=UIConfig.VSPACE_SMALL),  # Spacer
            ft.Row(
                controls=[
                    left_column,
                    controls.section_containers[2],  # Project Structure
                ],
                spacing=UIConfig.SPACING_LARGE,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                controls.progress_bar,
                                controls.progress_step_text,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        ft.Row(
                            [
                                controls.progress_ring,
                                controls.status_icon,
                                controls.status_text,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8,
                        ),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ),
            ft.Row(
                controls=[controls.build_project_button],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Divider(height=UIConfig.SPACING_LARGE),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def render_packages_panel(state: AppState, controls: Controls) -> ft.Control:
    """Render the declarative packages panel for the imperative main view.

    PackagesPanel is an `@ft.component`, so it can only be called inside a
    renderer. The app is otherwise imperative, so this one subtree gets its own
    `Renderer` — `page.render()` would take over `views[0]` and flip the whole
    session into components mode.

    `ft.memo` is required, not an optimization: without it every imperative
    `page.update()` re-renders the body into fresh control ids without patching
    the client, and every click inside the panel is silently dropped. Memoized,
    an unchanged parent update reuses the previous render; an explicit
    `controls.packages_panel.update()` re-renders *and* patches.

    Args:
        state: Application state, passed as a getter so the component is not
            subscribed to it (see `uv_forger.ui.packages_panel`).
        controls: Holds `on_package_select`, wired later by `attach_handlers`.

    Returns:
        The rendered `Component` to drop into the layout.
    """
    return Renderer().render(
        lambda: ft.memo(PackagesPanel)(
            lambda: state,
            lambda idx: controls.on_package_select and controls.on_package_select(idx),
        )
    )


def build_main_view(page: ft.Page, state: AppState) -> ft.Control:
    """Build and return the main application UI layout.

    Creates all UI controls, arranges them in a column layout, and stores
    references on the page object for cross-module access.

    Args:
        page: The Flet page to attach controls and state references to.
        state: The application state instance to store on the page.

    Returns:
        The root Column control containing the complete UI layout.
    """
    colors = get_theme_colors(state.is_dark_mode)

    # Create all controls
    controls = create_controls(state, colors)

    # Organize controls into sections
    create_sections(controls, state)

    # Create app bars
    create_app_bars(page, controls, colors)

    # Create main layout
    layout = create_layout(controls)

    # Store references on page
    page.controls_ref = controls
    page.state_ref = state

    return layout
