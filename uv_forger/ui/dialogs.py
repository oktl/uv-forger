"""Reusable dialog components.

This module provides standardized, theme-aware dialog components
that maintain consistent styling and behavior across the application.

Design Note
-----------
This file is intentionally large. Each dialog function is a self-contained
mini-UI: it creates form fields, wires up local callbacks, manages internal
state, and returns a configured AlertDialog. Splitting them into separate
files was considered but rejected — the shared helpers (_create_dialog_title,
_create_dialog_actions, _build_badge_row, etc.) are used across many dialogs,
and the consistent pattern makes the file easy to navigate despite its size.
Pure data-transform logic (tree building) lives in tree_builder.py.

Table of Contents
=================

Content/documentation dialogs have been extracted to content_dialogs.py:
    create_dialog_text_field, create_help_dialog, create_app_cheat_sheet_dialog,
    create_about_dialog

Helpers (private)
-----------------
    create_tooltip .................. line ~75
    _create_dialog_title ............ line ~97
    _create_dialog_actions .......... line ~124
    _create_summary_row ............. line ~189
    _build_badge_row ................ line ~208
    _autofocus_selected_radio ....... line ~272
    _create_none_option_container ... line ~295
    _parse_log_location ............. line ~336
    _parse_log_line ................. line ~354

Public dialog functions
-----------------------
    create_confirm_dialog ........... line ~446
    _create_categorized_radio_dialog  line ~532  (shared by project type/framework)
    create_project_type_dialog ...... line ~664
    create_framework_dialog ......... line ~696
    create_add_item_dialog .......... line ~728
    create_build_error_dialog ....... line ~936
    create_add_packages_dialog ...... line ~997
    create_build_summary_dialog ..... line ~1246
    create_log_viewer_dialog ........ line ~1591
    create_metadata_dialog .......... line ~1663
    create_settings_dialog .......... line ~1768
    create_history_dialog ........... line ~2266
    create_presets_dialog ........... line ~2466
    create_file_editor_view ......... line ~2796
"""

from __future__ import annotations

import ast
import asyncio
import collections.abc
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from uv_forger.ui.theme_manager import get_theme_colors
from uv_forger.ui.tree_builder import build_project_tree_controls
from uv_forger.ui.ui_config import UIConfig

if TYPE_CHECKING:
    from uv_forger.core.models import BuildSummaryConfig


# ============================================================================
# Module-Level Helper Functions
# ============================================================================


def create_tooltip(description: str, packages: list[str] | str | None) -> str:
    """Create rich tooltip text with description and package info.

    Args:
        description: Main description text
        packages: Package name(s) - can be list, single string, or None

    Returns:
        Formatted tooltip string with description and package information
    """
    tooltip_lines = [description, ""]
    if isinstance(packages, list) and packages:
        tooltip_lines.append("📦 Packages:")
        for pkg in packages:
            tooltip_lines.append(f"  • {pkg}")
    elif isinstance(packages, str):
        tooltip_lines.append(f"📦 Package: {packages}")
    else:
        tooltip_lines.append("📦 No additional packages")
    return "\n".join(tooltip_lines)


def _create_dialog_title(
    text: str, colors: dict, icon: str | None = None, icon_size: int = 24
) -> ft.Control:
    """Create standardized dialog title with optional icon.

    Args:
        text: Title text
        colors: Theme colors dictionary
        icon: Optional icon name (Flet Icons constant)
        icon_size: Size of the icon in pixels

    Returns:
        Row with icon and text, or just Text if no icon
    """
    if icon:
        return ft.Row(
            [
                ft.Icon(icon, size=icon_size, color=colors["main_title"]),
                ft.Text(
                    text, size=UIConfig.DIALOG_TITLE_SIZE, color=colors["main_title"]
                ),
            ],
            spacing=8,
        )
    return ft.Text(text, size=UIConfig.DIALOG_TITLE_SIZE, color=colors["main_title"])


def _create_dialog_actions(
    primary_label: str,
    primary_callback,
    cancel_callback,
    primary_icon: str | None = None,
    is_dark_mode: bool = True,
    primary_autofocus: bool = True,
) -> list[ft.Control]:
    """Create standardized dialog action buttons.

    Both buttons show an obvious focused state (brighter shade + white border)
    matching the style used in confirmation dialogs.

    Args:
        primary_label: Label for primary action button
        primary_callback: Callback for primary action
        cancel_callback: Callback for cancel button
        primary_icon: Optional icon for primary button
        is_dark_mode: Whether dark mode is active
        primary_autofocus: Whether to autofocus the primary button (default True)

    Returns:
        List of action buttons [FilledButton, OutlinedButton]
    """
    primary = ft.FilledButton(
        primary_label,
        on_click=primary_callback,
        autofocus=primary_autofocus,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_600,
                ft.ControlState.FOCUSED: ft.Colors.BLUE_400,
                ft.ControlState.HOVERED: ft.Colors.BLUE_500,
                ft.ControlState.PRESSED: ft.Colors.BLUE_700,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
                ft.ControlState.HOVERED: ft.BorderSide(0, ft.Colors.TRANSPARENT),
            },
        ),
    )
    if primary_icon:
        primary.icon = primary_icon

    cancel_bg_focused = ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
    cancel = ft.OutlinedButton(
        "Cancel",
        on_click=cancel_callback,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                ft.ControlState.FOCUSED: cancel_bg_focused,
                ft.ControlState.HOVERED: cancel_bg_focused,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.GREY_500),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
                ft.ControlState.HOVERED: ft.BorderSide(1, ft.Colors.GREY_400),
            },
        ),
    )
    return [primary, cancel]


def _create_summary_row(label: str, value: str) -> ft.Row:
    """Create a row for build summary dialog.

    Args:
        label: Row label (e.g., "Project Name:")
        value: Row value

    Returns:
        Formatted Row with label and value
    """
    return ft.Row(
        [
            ft.Text(label, weight=ft.FontWeight.BOLD, size=13, width=130),
            ft.Text(value, size=13),
        ],
        spacing=8,
    )


def _build_badge_row(
    entry,
    include_dev: bool = False,
) -> list[ft.Control]:
    """Build a list of badge controls for a history entry or preset.

    Creates blue pill badges for framework/project type and grey italic
    text for package counts. Used by both history and presets dialogs.

    Args:
        entry: A ProjectHistoryEntry or ProjectPreset with ui_project_enabled,
            framework, other_project_enabled, project_type, packages, and
            optionally dev_packages attributes.
        include_dev: Whether to include a dev package count badge.

    Returns:
        List of Flet controls for display in a Row.
    """
    badge_row: list[ft.Control] = []

    if entry.ui_project_enabled and entry.framework:
        badge_row.append(
            ft.Container(
                content=ft.Text(entry.framework, size=11, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.BLUE_700,
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            )
        )
    if entry.other_project_enabled and entry.project_type:
        badge_row.append(
            ft.Container(
                content=ft.Text(entry.project_type, size=11, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.BLUE_700,
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            )
        )

    if entry.packages:
        pkg_count = len(entry.packages)
        badge_row.append(
            ft.Text(
                f"{pkg_count} pkg{'s' if pkg_count != 1 else ''}",
                size=11,
                color=ft.Colors.GREY_500,
                italic=True,
            )
        )

    if include_dev and getattr(entry, "dev_packages", None):
        dev_count = len(entry.dev_packages)
        badge_row.append(
            ft.Text(
                f"{dev_count} dev",
                size=11,
                color=ft.Colors.AMBER_400,
                italic=True,
            )
        )

    return badge_row


def _autofocus_selected_radio(controls: list[ft.Control], selected_value: str) -> None:
    """Set autofocus on the Radio whose value matches selected_value.

    Walks a flat list of Container controls, finds the Radio inside each,
    and sets autofocus=True on the one matching selected_value.
    """
    for control in controls:
        if not isinstance(control, ft.Container) or control.content is None:
            continue
        # Radio is either directly in the container or inside a Row
        radio = None
        if isinstance(control.content, ft.Radio):
            radio = control.content
        elif isinstance(control.content, ft.Row):
            for child in control.content.controls:
                if isinstance(child, ft.Radio):
                    radio = child
                    break
        if radio and radio.value == selected_value:
            radio.autofocus = True
            return


def _create_none_option_container(is_dark_mode: bool) -> list[ft.Control]:
    """Create 'None (Clear Selection)' radio option with divider.

    Styled distinctly from regular options (tinted bg + cancel icon) to
    signal that this is a clearing action rather than a normal selection.

    Args:
        is_dark_mode: Whether dark mode is active

    Returns:
        List containing the none option container and divider
    """
    bg_color = ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_200

    return [
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CANCEL, size=14, color=UIConfig.COLOR_ERROR),
                    ft.Radio(
                        value="_none_",
                        label="None (Clear Selection)",
                        label_style=ft.TextStyle(size=13, italic=True),
                    ),
                ],
                spacing=4,
            ),
            padding=ft.Padding(left=8, top=4, bottom=4, right=0),
            bgcolor=bg_color,
            tooltip="Clear selection and uncheck the checkbox",
            border_radius=4,
            ink=True,
        ),
        ft.Divider(
            height=1,
            thickness=1,
            color=ft.Colors.GREY_300 if not is_dark_mode else ft.Colors.GREY_700,
        ),
    ]


def _parse_log_location(location: str) -> tuple[str, int] | None:
    """Extract module path and line number from a log location segment.

    Args:
        location: Location string like ``app.core.state:load:42``.

    Returns:
        Tuple of (dotted module path, line number) or None if unparseable.
    """
    parts = location.strip().split(":")
    if len(parts) >= 3:
        try:
            return parts[0], int(parts[-1])
        except ValueError:
            return None
    return None


def _parse_log_line(
    line: str,
    is_dark_mode: bool,
    on_location_click: collections.abc.Callable[[str, int], None] | None = None,
) -> ft.Row:
    """Parse a single log line into a colored Flet Row.

    Expected format: ``{time} | {level} | {name}:{function}:{line} - {message}``

    Args:
        line: Raw log line string.
        is_dark_mode: Whether dark mode is active.
        on_location_click: Optional callback ``(module_path, line_number)`` invoked
            when the location segment is clicked.

    Returns:
        A Row with coloured Text segments for each part of the log line.
    """
    level_colors = {
        "DEBUG": ft.Colors.GREY_600,
        "INFO": ft.Colors.GREY_400 if is_dark_mode else ft.Colors.GREY_700,
        "SUCCESS": ft.Colors.GREEN_400,
        "WARNING": ft.Colors.AMBER_400,
        "ERROR": ft.Colors.RED_400,
        "CRITICAL": ft.Colors.RED_300,
    }

    text_kwargs = {"font_family": "monospace", "size": 11, "no_wrap": True}

    parts = line.split(" | ", 2)
    if len(parts) != 3:
        return ft.Row(
            [ft.Text(line, color=ft.Colors.GREY_600, **text_kwargs)],
            spacing=0,
            tight=True,
        )

    timestamp, level_raw, rest = parts
    level = level_raw.strip()
    color = level_colors.get(level, ft.Colors.GREY_600)
    weight = ft.FontWeight.BOLD if level == "CRITICAL" else None

    loc_msg = rest.split(" - ", 1)
    location = loc_msg[0] if len(loc_msg) == 2 else rest
    message = loc_msg[1] if len(loc_msg) == 2 else ""

    # Build the location control — clickable if a callback is provided
    loc_parsed = _parse_log_location(location) if on_location_click else None
    if loc_parsed and on_location_click:
        module_path, line_no = loc_parsed

        loc_text = ft.Text(location, color=ft.Colors.CYAN_400, **text_kwargs)

        def _on_hover(e, txt=loc_text):
            txt.text_decorations = (
                ft.TextDecoration.UNDERLINE
                if e.data == "true"
                else ft.TextDecoration.NONE
            )
            txt.update()

        def _on_click(_e, mp=module_path, ln=line_no):
            on_location_click(mp, ln)

        location_control = ft.GestureDetector(
            content=loc_text,
            on_hover=_on_hover,
            on_tap=_on_click,
            mouse_cursor=ft.MouseCursor.CLICK,
        )
    else:
        location_control = ft.Text(location, color=ft.Colors.CYAN_400, **text_kwargs)

    controls = [
        ft.Text(timestamp, color=ft.Colors.GREY_600, **text_kwargs),
        ft.Text(" | ", color=ft.Colors.GREY_700, **text_kwargs),
        ft.Text(level_raw, color=color, weight=weight, **text_kwargs),
        ft.Text(" | ", color=ft.Colors.GREY_700, **text_kwargs),
        location_control,
    ]
    if message:
        controls.append(ft.Text(" - ", color=ft.Colors.GREY_700, **text_kwargs))
        controls.append(ft.Text(message, color=color, weight=weight, **text_kwargs))

    return ft.Row(controls, spacing=0, tight=True)


# ============================================================================
# Public Dialog Functions
# ============================================================================


def create_confirm_dialog(
    title: str,
    message: str,
    confirm_label: str,
    on_confirm,
    on_cancel,
    is_dark_mode: bool,
    confirm_icon: str | None = None,
) -> ft.AlertDialog:
    """Create a simple confirmation dialog with confirm and cancel actions.

    The confirm button receives autofocus so pressing Enter immediately triggers
    it. Both buttons show an obvious focused state when tabbing between them.

    Args:
        title: Dialog title text
        message: Body message to display
        confirm_label: Label for the confirm button
        on_confirm: Callback when confirm is clicked
        on_cancel: Callback when cancel is clicked
        is_dark_mode: Whether dark mode is active
        confirm_icon: Optional icon for the confirm button

    Returns:
        Configured AlertDialog
    """
    colors = get_theme_colors(is_dark_mode)

    # Confirm button — autofocused so Enter triggers it immediately.
    # Focused state uses a BRIGHTER shade (not darker) so it stands out
    # against the dark dialog background, plus a white border ring.
    confirm_btn = ft.FilledButton(
        confirm_label,
        on_click=on_confirm,
        autofocus=True,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_600,
                ft.ControlState.FOCUSED: ft.Colors.BLUE_400,
                ft.ControlState.HOVERED: ft.Colors.BLUE_500,
                ft.ControlState.PRESSED: ft.Colors.BLUE_700,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
                ft.ControlState.HOVERED: ft.BorderSide(0, ft.Colors.TRANSPARENT),
            },
        ),
    )
    if confirm_icon:
        confirm_btn.icon = confirm_icon

    # Cancel button — outlined at rest, fills with grey + white border when focused.
    cancel_bg_focused = ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
    cancel_btn = ft.OutlinedButton(
        "Cancel",
        on_click=on_cancel,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                ft.ControlState.FOCUSED: cancel_bg_focused,
                ft.ControlState.HOVERED: cancel_bg_focused,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.GREY_500),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
                ft.ControlState.HOVERED: ft.BorderSide(1, ft.Colors.GREY_400),
            },
        ),
    )

    return ft.AlertDialog(
        modal=True,
        title=_create_dialog_title(
            title, colors, icon=ft.Icons.WARNING_AMBER_ROUNDED, icon_size=20
        ),
        content=ft.Container(
            content=ft.Text(message, size=14, color=colors.get("section_title")),
            width=360,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=[confirm_btn, cancel_btn],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def _create_categorized_radio_dialog(
    title: str,
    icon: str,
    categories: dict,
    package_map: dict,
    on_select_callback,
    on_close_callback,
    current_selection: str | None,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create a categorized radio-button selection dialog.

    Shared implementation for project type and UI framework dialogs.

    Args:
        title: Dialog title text (e.g., "Select Project Type")
        icon: Flet Icons constant for the title
        categories: Category dict (e.g., PROJECT_TYPE_CATEGORIES)
        package_map: Package mapping dict for tooltip generation
        on_select_callback: Callback function(selected_value) when Select is clicked.
            Receives None if "None (Clear Selection)" is chosen.
        on_close_callback: Callback function when Cancel is clicked
        current_selection: Currently selected value (or None)
        is_dark_mode: Whether dark mode is active

    Returns:
        Configured AlertDialog for selection
    """
    colors = get_theme_colors(is_dark_mode)

    dialog_controls = []
    dialog_controls.extend(_create_none_option_container(is_dark_mode))

    category_names = list(categories.keys())
    for category_name, category_data in categories.items():
        light_color = getattr(
            ft.Colors, category_data["light_color"], ft.Colors.GREY_50
        )
        dark_color = getattr(ft.Colors, category_data["dark_color"], ft.Colors.GREY_900)
        bg_color = light_color if not is_dark_mode else dark_color

        dialog_controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(category_data["icon"], size=16),
                        ft.Text(
                            category_name,
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["section_title"],
                        ),
                    ],
                    spacing=8,
                ),
                bgcolor=bg_color,
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                border_radius=6,
                margin=ft.Margin(top=8, bottom=4, left=0, right=0),
            )
        )

        selected_bgcolor = ft.Colors.BLUE_900 if is_dark_mode else ft.Colors.BLUE_50
        for label, value, description in category_data["items"]:
            packages = package_map.get(value) or []
            tooltip_text = create_tooltip(description, packages)

            dialog_controls.append(
                ft.Container(
                    content=ft.Radio(
                        value=value,
                        label=label,
                        label_style=ft.TextStyle(size=13),
                    ),
                    padding=ft.Padding(left=32, top=2, bottom=2, right=0),
                    tooltip=tooltip_text,
                    border_radius=4,
                    ink=True,
                    bgcolor=selected_bgcolor if value == current_selection else None,
                )
            )

        if category_name != category_names[-1]:
            dialog_controls.append(
                ft.Divider(
                    height=1,
                    thickness=1,
                    color=ft.Colors.GREY_300
                    if not is_dark_mode
                    else ft.Colors.GREY_700,
                )
            )

    selected = current_selection or "_none_"
    _autofocus_selected_radio(dialog_controls, selected)

    radio_column = ft.Column(
        controls=dialog_controls,
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )

    radio_group = ft.RadioGroup(
        content=radio_column,
        value=selected,
    )

    def on_select_click(e):
        selected_value = radio_group.value
        on_select_callback(None if selected_value == "_none_" else selected_value)

    return ft.AlertDialog(
        modal=True,
        title=_create_dialog_title(title, colors, icon),
        content=ft.Container(
            content=radio_group,
            width=520,
            height=550,
            padding=12,
        ),
        actions=_create_dialog_actions(
            "Select",
            on_select_click,
            on_close_callback,
            ft.Icons.CHECK_CIRCLE_OUTLINE,
            is_dark_mode,
            primary_autofocus=False,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )


def create_project_type_dialog(
    on_select_callback,
    on_close_callback,
    current_selection: str | None,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create dialog for selecting project type with rich tooltips and styling.

    Args:
        on_select_callback: Callback receiving the selected project type string, or None if cleared.
        on_close_callback: Callback when Cancel is clicked.
        current_selection: Currently selected project type, or None.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog with categorized radio selection.
    """
    from uv_forger.core.constants import PROJECT_TYPE_PACKAGE_MAP
    from uv_forger.ui.dialog_data import PROJECT_TYPE_CATEGORIES

    return _create_categorized_radio_dialog(
        title="Select Project Type",
        icon=ft.Icons.FOLDER_SPECIAL,
        categories=PROJECT_TYPE_CATEGORIES,
        package_map=PROJECT_TYPE_PACKAGE_MAP,
        on_select_callback=on_select_callback,
        on_close_callback=on_close_callback,
        current_selection=current_selection,
        is_dark_mode=is_dark_mode,
    )


def create_framework_dialog(
    on_select_callback,
    on_close_callback,
    current_selection: str | None,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create dialog for selecting UI framework with rich tooltips.

    Args:
        on_select_callback: Callback receiving the selected framework string, or None if cleared.
        on_close_callback: Callback when Cancel is clicked.
        current_selection: Currently selected framework, or None.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog with categorized radio selection.
    """
    from uv_forger.core.constants import FRAMEWORK_PACKAGE_MAP
    from uv_forger.ui.dialog_data import UI_FRAMEWORK_CATEGORIES

    return _create_categorized_radio_dialog(
        title="Select UI Framework",
        icon=ft.Icons.WIDGETS,
        categories=UI_FRAMEWORK_CATEGORIES,
        package_map=FRAMEWORK_PACKAGE_MAP,
        on_select_callback=on_select_callback,
        on_close_callback=on_close_callback,
        current_selection=current_selection,
        is_dark_mode=is_dark_mode,
    )


def create_add_item_dialog(
    on_add_callback,
    on_close_callback,
    parent_folders: list[dict],
    is_dark_mode: bool,
    on_browse_callback=None,
    on_browse_folder_callback=None,
) -> ft.AlertDialog:
    """Create dialog for adding a folder or file.

    Args:
        on_add_callback: Callback function(name, item_type, parent_path, content) when Add is clicked
        on_close_callback: Callback function when Cancel is clicked
        parent_folders: List of parent folder options [{"label": "core/", "path": [0]}, ...]
        is_dark_mode: Whether dark mode is active
        on_browse_callback: Optional async callback for browsing files from disk
        on_browse_folder_callback: Optional async callback for browsing folders from disk

    Returns:
        Configured AlertDialog for adding items
    """
    from uv_forger.core.validator import validate_folder_name

    colors = get_theme_colors(is_dark_mode)

    # Mutable containers for imported content
    imported_content: list[str | None] = [None]
    imported_folder_data: list[tuple | None] = [None]

    # Warning banner for validation errors (defined first so it can be referenced)
    warning_text = ft.Text(
        value="",
        color=UIConfig.COLOR_WARNING,
        size=13,
        visible=False,
        weight=ft.FontWeight.W_500,
    )

    def on_name_change(e):
        """Validate name input in real-time."""
        name = e.control.value if e.control.value else ""

        if not name:
            # Empty input - hide warning
            warning_text.value = ""
            warning_text.visible = False
        else:
            # Validate the name
            is_valid, error_msg = validate_folder_name(name)
            if is_valid:
                # Valid input - clear warning
                warning_text.value = ""
                warning_text.visible = False
            else:
                # Invalid input - show warning
                warning_text.value = error_msg
                warning_text.visible = True

        e.page.update()

    # Input fields
    name_field = ft.TextField(
        label="Name",
        hint_text="Enter folder or file name",
        width=400,
        autofocus=True,
        on_change=on_name_change,
    )

    # Browse file button and feedback text (visible only when type == "file")
    browse_feedback = ft.Text(
        value="No file selected",
        size=12,
        color=colors["status_default"],
        italic=True,
        visible=False,
    )

    def _on_browse_click(e):
        """Handle Browse button click — delegates to handler callback."""
        if on_browse_callback:
            asyncio.create_task(
                on_browse_callback(name_field, imported_content, browse_feedback)
            )

    browse_button = ft.TextButton(
        content=ft.Text("Browse..."),
        icon=ft.Icons.FOLDER_OPEN,
        on_click=_on_browse_click,
    )

    browse_row = ft.Row(
        [browse_button, browse_feedback],
        visible=False,
        spacing=10,
    )

    # Browse folder button and feedback text (visible only when type == "folder")
    browse_folder_feedback = ft.Text(
        value="No folder selected",
        size=12,
        color=colors["status_default"],
        italic=True,
        visible=False,
    )

    def _on_browse_folder_click(e):
        """Handle Browse Folder button click — delegates to handler callback."""
        if on_browse_folder_callback:
            asyncio.create_task(
                on_browse_folder_callback(
                    name_field, imported_folder_data, browse_folder_feedback
                )
            )

    browse_folder_button = ft.TextButton(
        content=ft.Text("Import from Disk..."),
        icon=ft.Icons.DRIVE_FOLDER_UPLOAD,
        on_click=_on_browse_folder_click,
    )

    browse_folder_row = ft.Row(
        [browse_folder_button, browse_folder_feedback],
        visible=on_browse_folder_callback is not None,
        spacing=10,
    )

    # Type selection
    def on_type_change(e):
        """Toggle browse row visibility based on type selection."""
        is_file = type_radio.value == "file"
        browse_row.visible = is_file and on_browse_callback is not None
        browse_folder_row.visible = (
            not is_file and on_browse_folder_callback is not None
        )
        # Clear imported content when switching types
        if is_file:
            imported_folder_data[0] = None
            browse_folder_feedback.value = "No folder selected"
            browse_folder_feedback.visible = False
        else:
            imported_content[0] = None
            browse_feedback.value = "No file selected"
            browse_feedback.visible = False
        e.page.update()

    type_radio = ft.RadioGroup(
        content=ft.Row(
            [
                ft.Radio(value="folder", label="Folder"),
                ft.Radio(value="file", label="File"),
            ]
        ),
        value="folder",
        on_change=on_type_change,
    )

    # Parent folder dropdown
    parent_options = [ft.dropdown.Option(key="root", text="Root")]
    for folder in parent_folders:
        parent_options.append(
            ft.dropdown.Option(key=str(folder["path"]), text=folder["label"])
        )

    parent_dropdown = ft.Dropdown(
        label="Parent Location",
        hint_text="Select parent folder",
        options=parent_options,
        value="root",
        width=400,
        dense=True,
        text_size=13,
        menu_height=300,
    )

    def on_add_click(e):
        """Handle Add button click with validation."""
        name = name_field.value

        # Validate name before proceeding
        if not name:
            warning_text.value = "Name cannot be empty"
            warning_text.visible = True
            e.page.update()
            return

        is_valid, error_msg = validate_folder_name(name)
        if not is_valid:
            warning_text.value = error_msg
            warning_text.visible = True
            e.page.update()
            return

        # Name is valid, proceed with adding
        item_type = type_radio.value
        parent_value = parent_dropdown.value

        # Parse parent path
        if parent_value == "root":
            parent_path = None
        else:
            _parse_errors = (ValueError, SyntaxError)
            try:
                parent_path = ast.literal_eval(parent_value)
            except _parse_errors:
                parent_path = None

        # Determine content to pass
        if item_type == "folder" and imported_folder_data[0] is not None:
            content = imported_folder_data[0]
        elif item_type == "file":
            content = imported_content[0]
        else:
            content = None
        on_add_callback(name, item_type, parent_path, content)

    name_field.on_submit = on_add_click

    dialog = ft.AlertDialog(
        modal=True,
        title=_create_dialog_title(
            "Add File or Folder", colors, icon=ft.Icons.ADD_CIRCLE_OUTLINE
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    name_field,
                    warning_text,
                    browse_row,
                    browse_folder_row,
                    ft.Container(height=10),
                    ft.Text("Type:", size=14),
                    type_radio,
                    ft.Container(height=10),
                    parent_dropdown,
                ],
                tight=True,
            ),
            width=450,
            padding=20,
        ),
        actions=[
            ft.TextButton("Add", on_click=on_add_click),
            ft.TextButton("Cancel", on_click=on_close_callback),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Store warning text reference on dialog for callback access
    dialog.warning_text = warning_text

    return dialog


def create_build_error_dialog(
    error_message: str,
    on_close_callback,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create a dialog displaying a build failure with its full error output.

    Args:
        error_message: Full error detail string from the failed build.
        on_close_callback: Callback when the Close button is clicked.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog showing the build error.
    """
    colors = get_theme_colors(is_dark_mode)

    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=UIConfig.COLOR_ERROR, size=24),
                ft.Text(
                    "Build Failed",
                    size=UIConfig.DIALOG_TITLE_SIZE,
                    color=UIConfig.COLOR_ERROR,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=8,
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "The build did not complete. Full error details:",
                        size=13,
                        color=colors.get("section_title"),
                    ),
                    ft.Container(height=8),
                    ft.TextField(
                        value=error_message,
                        read_only=True,
                        multiline=True,
                        min_lines=6,
                        max_lines=12,
                        text_style=ft.TextStyle(size=12, font_family="monospace"),
                        border_color=UIConfig.COLOR_ERROR,
                        width=500,
                    ),
                ],
                tight=True,
            ),
            width=540,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=[ft.TextButton("Close", on_click=on_close_callback)],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def create_add_packages_dialog(
    on_add_callback,
    on_close_callback,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create dialog for adding one or more packages to the install list.

    Includes an opt-in "Verify on PyPI" button that checks each package
    against the PyPI registry asynchronously. Results are informational
    only — the Add button works regardless of check results.

    Args:
        on_add_callback: Callback function(packages: list[str], dev: bool)
            called with parsed names and whether they should be dev deps.
        on_close_callback: Callback function when Cancel is clicked.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog for adding packages.
    """
    import asyncio

    from uv_forger.core.pypi_checker import (
        check_pypi_availability,
        extract_package_name,
        validate_package_format,
    )

    colors = get_theme_colors(is_dark_mode)

    warning_text = ft.Text(
        value="",
        color=UIConfig.COLOR_WARNING,
        size=13,
        visible=False,
        weight=ft.FontWeight.W_500,
    )

    packages_field = ft.TextField(
        label="Packages",
        hint_text="One package per line, or comma-separated\ne.g.\nrequests\nhttpx>=0.25\ndjango[postgres]\npytest==8.0",
        multiline=True,
        min_lines=4,
        max_lines=8,
        width=400,
        autofocus=True,
    )

    dev_checkbox = ft.Checkbox(
        label="Add as dev dependencies",
        value=False,
        tooltip="Dev dependencies are installed with 'uv add --dev'\nand go into [dependency-groups] in pyproject.toml.",
    )

    dev_row = ft.Row(
        controls=[
            dev_checkbox,
            ft.Icon(
                ft.Icons.INFO_OUTLINE,
                size=12,
                color=UIConfig.COLOR_INFO,
                tooltip=(
                    "Dev dependencies are installed with 'uv add --dev'\n"
                    "and placed in [dependency-groups] in pyproject.toml.\n"
                    "Examples: pytest, ruff, mypy — tools not needed at runtime."
                ),
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Results area for PyPI verification — hidden until first verify click
    results_column = ft.Column(
        scroll=ft.ScrollMode.AUTO, height=120, visible=False, spacing=4
    )

    def _parse_packages() -> list[str]:
        """Parse package specs from the text field."""
        raw = packages_field.value or ""
        tokens = [
            token.strip() for part in raw.splitlines() for token in part.split(",")
        ]
        return [token for token in tokens if token]

    def _make_result_row(icon: str, icon_color: str, pkg: str, message: str) -> ft.Row:
        return ft.Row(
            [
                ft.Icon(icon, color=icon_color, size=16),
                ft.Text(pkg, size=12, weight=ft.FontWeight.W_500),
                ft.Text(f"— {message}", size=12, color=ft.Colors.GREY_500),
            ],
            spacing=6,
            tight=True,
        )

    def _make_checking_row(pkg: str) -> ft.Row:
        return ft.Row(
            [
                ft.ProgressRing(width=14, height=14, stroke_width=2),
                ft.Text(pkg, size=12, weight=ft.FontWeight.W_500),
                ft.Text("— Checking...", size=12, color=ft.Colors.GREY_500),
            ],
            spacing=6,
            tight=True,
        )

    async def _verify_packages(e):
        """Check each package against PyPI."""
        packages = _parse_packages()
        if not packages:
            warning_text.value = "Enter at least one package name to verify."
            warning_text.visible = True
            e.page.update()
            return

        warning_text.visible = False
        results_column.controls.clear()
        results_column.visible = True

        # First pass: client-side format validation + show checking spinners
        valid_packages: list[tuple[int, str]] = []  # (index, spec)
        for pkg in packages:
            fmt_error = validate_package_format(pkg)
            if fmt_error:
                results_column.controls.append(
                    _make_result_row(
                        ft.Icons.CANCEL, UIConfig.COLOR_ERROR, pkg, fmt_error
                    )
                )
            else:
                idx = len(results_column.controls)
                results_column.controls.append(_make_checking_row(pkg))
                valid_packages.append((idx, pkg))

        e.page.update()

        # Second pass: async PyPI lookups
        for idx, pkg in valid_packages:
            bare_name = extract_package_name(pkg)
            result = await check_pypi_availability(bare_name)

            if result is False:
                # Package exists on PyPI — that's good for an install
                row = _make_result_row(
                    ft.Icons.CHECK_CIRCLE,
                    UIConfig.COLOR_SUCCESS,
                    pkg,
                    "Found on PyPI",
                )
            elif result is True:
                # Package NOT on PyPI — warn user
                row = _make_result_row(
                    ft.Icons.ERROR_OUTLINE,
                    UIConfig.COLOR_WARNING,
                    pkg,
                    "Not found on PyPI",
                )
            else:
                # Network error
                row = _make_result_row(
                    ft.Icons.WIFI_OFF,
                    UIConfig.COLOR_WARNING,
                    pkg,
                    "Could not check",
                )

            results_column.controls[idx] = row
            e.page.update()

    def _wrap_verify(e):
        asyncio.create_task(_verify_packages(e))

    verify_button = ft.Button(
        "Verify on PyPI",
        icon=ft.Icons.TRAVEL_EXPLORE,
        on_click=_wrap_verify,
    )

    def on_add_click(e):
        packages = _parse_packages()
        if not packages:
            warning_text.value = "Enter at least one package name."
            warning_text.visible = True
            e.page.update()
            return

        # Client-side format validation before adding
        errors = []
        for pkg in packages:
            fmt_error = validate_package_format(pkg)
            if fmt_error:
                errors.append(fmt_error)

        if errors:
            warning_text.value = "\n".join(errors)
            warning_text.visible = True
            e.page.update()
            return

        warning_text.visible = False
        on_add_callback(packages, dev_checkbox.value)

    dialog = ft.AlertDialog(
        modal=True,
        title=_create_dialog_title(
            "Add Packages", colors, icon=ft.Icons.ADD_CIRCLE_OUTLINE
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Enter package names to add to the install list.\n"
                        "Version specifiers (>=, ==, <) and extras "
                        "([postgres], [dev]) are supported.",
                        size=13,
                        color=colors.get("section_title"),
                    ),
                    ft.Container(height=8),
                    packages_field,
                    dev_row,
                    ft.Row([verify_button], spacing=8),
                    warning_text,
                    results_column,
                ],
                tight=True,
                spacing=8,
            ),
            width=450,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=_create_dialog_actions(
            "Add",
            on_add_click,
            on_close_callback,
            ft.Icons.ADD,
            is_dark_mode,
            primary_autofocus=False,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Expose for testing
    dialog.verify_button = verify_button
    dialog.results_column = results_column

    return dialog


def create_build_summary_dialog(
    config: BuildSummaryConfig,
    on_build_callback,
    on_cancel_callback,
    is_dark_mode: bool,
    ide_name: str = "VS Code",
    open_folder_default: bool = False,
    open_terminal_default: bool = False,
) -> ft.AlertDialog:
    """Create a confirmation dialog showing project summary before build.

    Args:
        config: BuildSummaryConfig with all project configuration details
        on_build_callback: Callback when Build is clicked
        on_cancel_callback: Callback when Cancel is clicked
        is_dark_mode: Whether dark mode is active
        ide_name: Display name of the preferred IDE for the open-in checkbox.
        open_folder_default: Initial value for the open folder checkbox.
        open_terminal_default: Initial value for the open terminal checkbox.

    Returns:
        Configured AlertDialog with project summary
    """
    colors = get_theme_colors(is_dark_mode)

    rows = [
        _create_summary_row("Project Name:", config.project_name),
        _create_summary_row("Location:", config.project_path),
        _create_summary_row("Python Version:", config.python_version),
        _create_summary_row("Git Init:", "Yes" if config.git_enabled else "No"),
    ]

    if config.git_enabled:
        from uv_forger.core.constants import GIT_REMOTE_MODE_LABELS

        mode_label = GIT_REMOTE_MODE_LABELS.get(
            config.git_remote_mode, config.git_remote_mode
        )
        rows.append(_create_summary_row("Git Remote:", mode_label))
        if config.git_remote_mode == "github":
            gh_info = config.github_username or "(default account)"
            visibility = "private" if config.github_repo_private else "public"
            rows.append(_create_summary_row("GitHub:", f"{gh_info} ({visibility})"))

    starter_label = "Yes" if config.starter_files else "No"
    if config.file_override_count:
        starter_label += f" ({config.file_override_count} file{'s' if config.file_override_count != 1 else ''} with custom content)"
    rows += [
        _create_summary_row("Starter Files:", starter_label),
    ]

    if config.framework:
        rows.append(_create_summary_row("UI Framework:", config.framework))
    if config.project_type:
        type_name = config.project_type.replace("_", " ").title()
        rows.append(_create_summary_row("Project Type:", type_name))

    if config.author_name or config.author_email:
        author_display = config.author_name
        if config.author_email:
            author_display += (
                f" <{config.author_email}>" if author_display else config.author_email
            )
        rows.append(_create_summary_row("Author:", author_display))
    if config.description:
        rows.append(_create_summary_row("Description:", config.description))
    if config.license_type:
        rows.append(_create_summary_row("License:", config.license_type))

    # Collapsible project tree preview
    tree_controls = build_project_tree_controls(config)
    tree_container = ft.Container(
        content=ft.Column(
            tree_controls,
            scroll=ft.ScrollMode.AUTO,
            spacing=1,
            tight=True,
        ),
        width=400,
        height=200,
        padding=ft.Padding(left=8, top=4, right=4, bottom=4),
    )

    structure_label = f"{config.folder_count} folders, {config.file_count} files"
    tree_tile = ft.ExpansionTile(
        title=ft.Text("Structure", weight=ft.FontWeight.BOLD, size=13),
        subtitle=ft.Text(structure_label, size=12),
        controls=[tree_container],
        expanded=False,
        tile_padding=ft.Padding(left=0, top=0, right=0, bottom=0),
        controls_padding=ft.Padding(left=0, top=0, right=0, bottom=0),
    )
    rows.append(tree_tile)

    if config.packages:
        count = len(config.packages)
        dev_set = set(config.dev_packages)
        pkg_rows = []
        for pkg in config.packages:
            label = f"  • {pkg}"
            if pkg in dev_set:
                label += "  (dev)"
            pkg_rows.append(ft.Text(label, size=12))
        rows.append(
            ft.Row(
                [
                    ft.Text("Packages:", weight=ft.FontWeight.BOLD, size=13, width=130),
                    ft.Column(
                        [
                            ft.Text(
                                f"{count} package{'s' if count != 1 else ''}",
                                size=13,
                                color=colors.get("section_title"),
                            ),
                            *pkg_rows,
                        ],
                        spacing=2,
                        tight=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    else:
        rows.append(_create_summary_row("Packages:", "None"))

    def on_checkbox_change(e):
        e.control.label_style = (
            ft.TextStyle(color=UIConfig.COLOR_CHECKBOX_ACTIVE)
            if e.control.value
            else None
        )
        e.page.update()

    green = ft.TextStyle(color=UIConfig.COLOR_CHECKBOX_ACTIVE)

    open_folder_checkbox = ft.Checkbox(
        label="Open project folder after build",
        value=open_folder_default,
        label_style=green if open_folder_default else None,
        on_change=on_checkbox_change,
    )

    open_vscode_checkbox = ft.Checkbox(
        label=f"Open in {ide_name}",
        value=True,
        label_style=green,
        on_change=on_checkbox_change,
    )

    open_folder_row = ft.Row(
        [
            ft.Icon(ft.Icons.FOLDER_OPEN, size=16, color=UIConfig.COLOR_FOLDER_ICON),
            open_folder_checkbox,
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    open_vscode_row = ft.Row(
        [
            ft.Icon(ft.Icons.CODE, size=16, color=UIConfig.COLOR_INFO),
            open_vscode_checkbox,
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    open_terminal_checkbox = ft.Checkbox(
        label="Open terminal at project root",
        value=open_terminal_default,
        label_style=green if open_terminal_default else None,
        on_change=on_checkbox_change,
    )

    open_terminal_row = ft.Row(
        [
            ft.Icon(ft.Icons.TERMINAL, size=16, color=ft.Colors.GREY_400),
            open_terminal_checkbox,
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    post_build_command_field = ft.TextField(
        value=config.post_build_command,
        hint_text="e.g. uv run pre-commit install",
        width=400,
        text_size=13,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        disabled=not config.post_build_command_enabled,
    )

    post_build_enabled = config.post_build_command_enabled
    post_build_checkbox = ft.Checkbox(
        label="Run post-build command",
        value=post_build_enabled,
        label_style=green if post_build_enabled else None,
        on_change=on_checkbox_change,
    )

    def on_post_build_toggle(e):
        post_build_command_field.disabled = not e.control.value
        e.control.label_style = (
            ft.TextStyle(color=UIConfig.COLOR_CHECKBOX_ACTIVE)
            if e.control.value
            else None
        )
        e.page.update()

    post_build_checkbox.on_change = on_post_build_toggle

    post_build_row = ft.Row(
        [
            ft.Icon(ft.Icons.PLAY_ARROW, size=16, color=ft.Colors.GREY_400),
            post_build_checkbox,
            ft.Icon(
                ft.Icons.INFO_OUTLINE,
                size=12,
                color=UIConfig.COLOR_INFO,
                tooltip=(
                    "Runs a shell command after a successful build.\n"
                    "Configure the default command in Settings.\n"
                    "Required packages are auto-added to the install list."
                ),
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    post_build_command_row = ft.Row(
        [
            ft.Container(width=22),
            ft.Text("Run:", size=12, color=colors.get("section_title")),
            post_build_command_field,
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --- Git remote mode override ---
    git_remote_controls: list[ft.Control] = []
    if config.git_enabled:
        from uv_forger.core.constants import GIT_REMOTE_MODE_LABELS

        git_remote_dropdown = ft.Dropdown(
            label="Git Remote",
            value=config.git_remote_mode,
            options=[
                ft.dropdown.Option(key=key, text=label)
                for key, label in GIT_REMOTE_MODE_LABELS.items()
            ],
            width=250,
            text_size=13,
        )

        git_remote_controls = [
            ft.Divider(height=8, thickness=1),
            ft.Text(
                "Git Remote",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=colors["section_title"],
            ),
            git_remote_dropdown,
        ]

    left_column = ft.Column(
        rows,
        tight=True,
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        width=450,
    )

    right_column = ft.Column(
        [
            ft.Text(
                "After Build",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=colors["section_title"],
            ),
            open_folder_row,
            open_vscode_row,
            open_terminal_row,
            ft.Divider(height=8, thickness=1),
            post_build_row,
            post_build_command_row,
            *git_remote_controls,
        ],
        tight=True,
        spacing=8,
        width=450,
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=_create_dialog_title("Confirm Build", colors, ft.Icons.BUILD_CIRCLE),
        content=ft.Container(
            content=ft.Row(
                [
                    left_column,
                    ft.VerticalDivider(width=20, thickness=1),
                    right_column,
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=0,
            ),
            width=960,
            padding=ft.Padding(left=20, top=20, right=40, bottom=20),
        ),
        actions=_create_dialog_actions(
            "Build",
            on_build_callback,
            on_cancel_callback,
            ft.Icons.ROCKET_LAUNCH,
            is_dark_mode,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    dialog.open_folder_checkbox = open_folder_checkbox
    dialog.open_ide_checkbox = open_vscode_checkbox
    # Keep legacy alias for backward compatibility in tests
    dialog.open_vscode_checkbox = open_vscode_checkbox
    dialog.open_terminal_checkbox = open_terminal_checkbox
    dialog.post_build_checkbox = post_build_checkbox
    dialog.post_build_command_field = post_build_command_field
    if config.git_enabled:
        dialog.git_remote_dropdown = git_remote_dropdown
        # Property-like access for the build handler
        dialog.git_remote_mode_value = git_remote_dropdown.value

        def _update_remote_mode(e):
            dialog.git_remote_mode_value = git_remote_dropdown.value

        git_remote_dropdown.on_change = _update_remote_mode
    else:
        dialog.git_remote_mode_value = None
    return dialog


def create_log_viewer_dialog(
    log_content: str,
    on_close_callback,
    is_dark_mode: bool,
    on_location_click: collections.abc.Callable[[str, int], None] | None = None,
) -> ft.AlertDialog:
    """Create a dialog displaying application log content with coloured lines.

    Args:
        log_content: Raw log file text.
        on_close_callback: Callback when the Close button is clicked.
        is_dark_mode: Whether dark mode is active.
        on_location_click: Optional callback ``(module_path, line_number)`` invoked
            when a clickable location segment is tapped.  When provided, location
            segments are rendered as hover-underline links.

    Returns:
        Configured AlertDialog with parsed, coloured log rows.
    """
    colors = get_theme_colors(is_dark_mode)

    parsed_rows = [
        _parse_log_line(line, is_dark_mode, on_location_click=on_location_click)
        for line in log_content.splitlines()
        if line.strip()
    ]

    if not parsed_rows:
        parsed_rows = [ft.Text("(empty log)", italic=True, color=ft.Colors.GREY_500)]

    log_text_ref = log_content

    def on_copy_click(e):
        import subprocess
        import sys

        try:
            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=log_text_ref.encode(), check=True)
            elif sys.platform == "win32":
                subprocess.run(["clip"], input=log_text_ref.encode(), check=True)
            else:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=log_text_ref.encode(),
                    check=True,
                )
            copy_btn.text = "Copied!"
        except (FileNotFoundError, subprocess.CalledProcessError):
            copy_btn.text = "Copy failed"
        e.page.update()

    copy_btn = ft.TextButton("Copy to Clipboard", on_click=on_copy_click)

    return ft.AlertDialog(
        modal=True,
        title=_create_dialog_title("Log Viewer", colors, icon=ft.Icons.ARTICLE),
        content=ft.Container(
            content=ft.Column(
                controls=parsed_rows,
                scroll=ft.ScrollMode.AUTO,
                auto_scroll=True,
            ),
            width=UIConfig.DIALOG_WIDTH,
            height=UIConfig.DIALOG_HEIGHT - 100,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=[copy_btn, ft.TextButton("Close", on_click=on_close_callback)],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def create_metadata_dialog(
    state,
    on_save_callback: collections.abc.Callable,
    on_close_callback: collections.abc.Callable,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create a dialog for editing project metadata fields.

    Args:
        state: Current AppState instance to populate fields from.
        on_save_callback: Callback receiving (author_name, author_email, description, license_type).
        on_close_callback: Callback when Cancel is clicked.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog for editing metadata.
    """
    from uv_forger.core.constants import LICENSE_TYPES

    colors = get_theme_colors(is_dark_mode)
    label_style = ft.TextStyle(size=13, color=colors["section_title"])

    field_width = 410

    author_name_field = ft.TextField(
        label="Author Name",
        value=state.author_name,
        width=field_width,
        label_style=label_style,
        autofocus=True,
    )

    author_email_field = ft.TextField(
        label="Author Email",
        value=state.author_email,
        width=field_width,
        label_style=label_style,
    )

    description_field = ft.TextField(
        label="Description",
        value=state.description,
        width=field_width,
        multiline=True,
        min_lines=2,
        max_lines=3,
        label_style=label_style,
    )

    license_options = [ft.dropdown.Option(key="", text="(None)")] + [
        ft.dropdown.Option(lt) for lt in LICENSE_TYPES
    ]
    license_dropdown = ft.Dropdown(
        label="License",
        value=state.license_type,
        options=license_options,
        width=field_width,
        label_style=label_style,
    )

    def on_save_click(_):
        on_save_callback(
            author_name_field.value or "",
            author_email_field.value or "",
            description_field.value or "",
            license_dropdown.value or "",
        )

    return ft.AlertDialog(
        modal=True,
        title=_create_dialog_title(
            "Project Metadata", colors, icon=ft.Icons.DESCRIPTION
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Set metadata fields for pyproject.toml.",
                        size=13,
                        color=colors.get("section_title"),
                    ),
                    ft.Container(height=8),
                    author_name_field,
                    author_email_field,
                    ft.Divider(height=16, color=colors.get("section_border")),
                    description_field,
                    license_dropdown,
                ],
                tight=True,
                spacing=10,
            ),
            width=450,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=_create_dialog_actions(
            "Save",
            on_save_click,
            on_close_callback,
            ft.Icons.SAVE,
            is_dark_mode,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )


def create_settings_dialog(
    settings,
    on_save_callback: collections.abc.Callable,
    on_close_callback: collections.abc.Callable,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create a dialog for editing user preferences.

    Args:
        settings: Current AppSettings instance to populate fields from.
        on_save_callback: Callback receiving the updated AppSettings on save.
        on_close_callback: Callback when Cancel is clicked or dialog dismissed.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog for editing settings.
    """
    from uv_forger.core.constants import (
        GIT_REMOTE_MODE_LABELS,
        LICENSE_TYPES,
        PYTHON_VERSIONS,
        SUPPORTED_IDES,
    )

    colors = get_theme_colors(is_dark_mode)

    label_style = ft.TextStyle(size=13, color=colors["section_title"])
    col_width = 460

    # --- Default project path ---
    project_path_field = ft.TextField(
        label="Default Project Path",
        value=settings.default_project_path,
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    async def browse_project_path(_):
        from uv_forger.ui.file_picker import select_folder

        result = await select_folder("Select Default Project Path")
        if result:
            project_path_field.value = result
            project_path_field.update()

    project_path_row = ft.Row(
        [
            project_path_field,
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                icon_size=UIConfig.ICON_SIZE_DEFAULT,
                tooltip="Browse",
                on_click=browse_project_path,
            ),
        ],
        spacing=4,
    )

    # --- Default GitHub root ---
    github_root_field = ft.TextField(
        label="Default GitHub Root",
        value=settings.default_github_root,
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    async def browse_github_root(_):
        from uv_forger.ui.file_picker import select_folder

        result = await select_folder("Select Default GitHub Root")
        if result:
            github_root_field.value = result
            github_root_field.update()

    github_root_row = ft.Row(
        [
            github_root_field,
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                icon_size=UIConfig.ICON_SIZE_DEFAULT,
                tooltip="Browse",
                on_click=browse_github_root,
            ),
        ],
        spacing=4,
    )

    # --- Default Python version ---
    python_version_dropdown = ft.Dropdown(
        label="Default Python Version",
        value=settings.default_python_version,
        options=[ft.dropdown.Option(v) for v in PYTHON_VERSIONS],
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    # --- Preferred IDE ---
    ide_names = list(SUPPORTED_IDES.keys())
    ide_dropdown = ft.Dropdown(
        label="Preferred IDE",
        value=settings.preferred_ide
        if settings.preferred_ide in ide_names
        else ide_names[0],
        options=[ft.dropdown.Option(name) for name in ide_names],
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    custom_ide_field = ft.TextField(
        label="Custom IDE Executable Path",
        value=settings.custom_ide_path,
        visible=settings.preferred_ide == "Other / Custom",
        expand=True,
        label_style=label_style,
        hint_text="/usr/local/bin/my-editor",
        dense=True,
        text_size=13,
    )

    def on_ide_change(e):
        custom_ide_field.visible = ide_dropdown.value == "Other / Custom"
        custom_ide_field.update()

    ide_dropdown.on_change = on_ide_change

    # --- Git init default ---
    git_checkbox = ft.Checkbox(
        label="Enable Git init by default",
        value=settings.git_enabled_default,
    )

    # --- Starter files default ---
    starter_files_checkbox = ft.Checkbox(
        label="Include starter files by default",
        value=settings.starter_files_default,
    )

    # --- Git remote mode ---
    git_remote_dropdown = ft.Dropdown(
        label="Git Remote Mode",
        value=settings.git_remote_mode,
        options=[
            ft.dropdown.Option(key=key, text=label)
            for key, label in GIT_REMOTE_MODE_LABELS.items()
        ],
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    github_username_field = ft.TextField(
        label="GitHub Username / Org",
        value=settings.github_username,
        expand=True,
        label_style=label_style,
        hint_text="(empty = your default account)",
        visible=settings.git_remote_mode == "github",
        dense=True,
        text_size=13,
    )

    github_private_checkbox = ft.Checkbox(
        label="Create private repos by default",
        value=settings.github_repo_private,
        visible=settings.git_remote_mode == "github",
    )

    gh_status_text = ft.Text("", size=12, visible=False)

    async def on_check_gh_status(_):
        from uv_forger.handlers.git_handler import (
            check_gh_authenticated,
            check_gh_available,
        )

        gh_status_text.visible = True
        if not check_gh_available():
            gh_status_text.value = "✗ gh CLI not installed"
            gh_status_text.color = ft.Colors.RED_400
        elif not check_gh_authenticated():
            gh_status_text.value = "✗ gh not authenticated — run 'gh auth login'"
            gh_status_text.color = ft.Colors.RED_400
        else:
            gh_status_text.value = "✓ gh authenticated"
            gh_status_text.color = ft.Colors.GREEN_400
        gh_status_text.update()

    gh_check_button = ft.TextButton(
        "Check gh status",
        icon=ft.Icons.VERIFIED_USER,
        on_click=on_check_gh_status,
        visible=settings.git_remote_mode == "github",
    )

    def on_remote_mode_change(e):
        mode = git_remote_dropdown.value
        is_local = mode == "local"
        is_github = mode == "github"
        github_root_row.visible = is_local
        github_username_field.visible = is_github
        github_private_checkbox.visible = is_github
        gh_check_button.visible = is_github
        gh_status_text.visible = False
        github_root_row.update()
        github_username_field.update()
        github_private_checkbox.update()
        gh_check_button.update()
        gh_status_text.update()

    git_remote_dropdown.on_change = on_remote_mode_change

    # Only show GitHub root row when mode is "local"
    github_root_row.visible = settings.git_remote_mode == "local"

    # --- Author defaults ---
    author_name_field = ft.TextField(
        label="Default Author Name",
        value=settings.default_author_name,
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    author_email_field = ft.TextField(
        label="Default Author Email",
        value=settings.default_author_email,
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    # --- Default license ---
    license_options = [ft.dropdown.Option(key="", text="(None)")] + [
        ft.dropdown.Option(lt) for lt in LICENSE_TYPES
    ]
    license_dropdown = ft.Dropdown(
        label="Default License",
        value=settings.default_license or "",
        options=license_options,
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    # --- After-build actions ---
    open_folder_checkbox = ft.Checkbox(
        label="Open project folder after build",
        value=settings.open_folder_default,
    )

    open_terminal_checkbox = ft.Checkbox(
        label="Open terminal at project root",
        value=settings.open_terminal_default,
    )

    # --- Post-build command ---
    post_build_enabled_checkbox = ft.Checkbox(
        label="Enable post-build command",
        value=settings.post_build_command_enabled,
    )

    post_build_command_field = ft.TextField(
        label="Post-build Command",
        value=settings.post_build_command,
        hint_text="uv run pre-commit install && uv run pytest",
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    post_build_packages_field = ft.TextField(
        label="Required Packages",
        value=settings.post_build_packages,
        hint_text="pre-commit, ruff",
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    # --- Custom templates path ---
    templates_path_field = ft.TextField(
        label="Custom Path (optional)",
        value=settings.custom_templates_path,
        expand=True,
        label_style=label_style,
        dense=True,
        text_size=13,
    )

    async def browse_templates_path(_):
        from uv_forger.ui.file_picker import select_folder

        result = await select_folder("Select Templates Directory")
        if result:
            templates_path_field.value = result
            templates_path_field.update()

    templates_path_row = ft.Row(
        [
            templates_path_field,
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                icon_size=UIConfig.ICON_SIZE_DEFAULT,
                tooltip="Browse",
                on_click=browse_templates_path,
            ),
        ],
        spacing=4,
    )

    # --- Save handler ---
    def on_save_click(_):
        from uv_forger.core.settings_manager import AppSettings

        updated = AppSettings(
            default_project_path=project_path_field.value
            or settings.default_project_path,
            default_github_root=github_root_field.value or settings.default_github_root,
            default_python_version=python_version_dropdown.value
            or settings.default_python_version,
            preferred_ide=ide_dropdown.value or settings.preferred_ide,
            custom_ide_path=custom_ide_field.value or "",
            git_enabled_default=git_checkbox.value,
            starter_files_default=starter_files_checkbox.value,
            default_author_name=author_name_field.value or "",
            default_author_email=author_email_field.value or "",
            default_license=license_dropdown.value or "",
            open_folder_default=open_folder_checkbox.value,
            open_terminal_default=open_terminal_checkbox.value,
            post_build_command=post_build_command_field.value or "",
            post_build_command_enabled=post_build_enabled_checkbox.value,
            post_build_packages=post_build_packages_field.value or "",
            git_remote_mode=git_remote_dropdown.value or "local",
            github_username=github_username_field.value or "",
            github_repo_private=github_private_checkbox.value,
            custom_templates_path=templates_path_field.value or "",
        )
        on_save_callback(updated)

    # --- Two-column layout helpers ---
    def _section_header(text: str, caption: str = "") -> ft.Control:
        children: list[ft.Control] = [
            ft.Text(
                text,
                weight=ft.FontWeight.W_600,
                size=14,
                color=colors["main_title"],
            )
        ]
        if caption:
            children.append(
                ft.Text(
                    caption,
                    size=11,
                    color=colors.get("section_title"),
                    italic=True,
                )
            )
        return ft.Column(children, spacing=1, tight=True)

    def _col_label(text: str) -> ft.Column:
        return ft.Column(
            [
                ft.Text(
                    text,
                    weight=ft.FontWeight.W_700,
                    size=15,
                    color=colors["main_title"],
                ),
                ft.Divider(height=4, color=colors.get("section_border")),
            ],
            spacing=4,
            tight=True,
        )

    left_col = ft.Column(
        [
            _col_label("Pre-Build"),
            _section_header("Paths", "Where new projects are created"),
            project_path_row,
            ft.Divider(height=4, color=colors.get("section_border")),
            _section_header("Defaults", "Pre-selected options for each new project"),
            python_version_dropdown,
            git_checkbox,
            starter_files_checkbox,
            ft.Divider(height=4, color=colors.get("section_border")),
            _section_header("Git Remote", "How new projects connect to a remote"),
            git_remote_dropdown,
            github_root_row,
            github_username_field,
            github_private_checkbox,
            ft.Row(
                [gh_check_button, gh_status_text],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(height=4, color=colors.get("section_border")),
            _section_header("Author", "Pre-filled in the Project Metadata dialog"),
            author_name_field,
            author_email_field,
            license_dropdown,
        ],
        tight=True,
        spacing=6,
    )

    right_col = ft.Column(
        [
            _col_label("Post-Build"),
            _section_header("IDE", "Choose your preferred IDE to open after build"),
            ide_dropdown,
            custom_ide_field,
            open_folder_checkbox,
            open_terminal_checkbox,
            ft.Divider(height=4, color=colors.get("section_border")),
            _section_header(
                "Automation", "Runs automatically after a successful build"
            ),
            ft.Row(
                controls=[
                    post_build_enabled_checkbox,
                    ft.Icon(
                        ft.Icons.INFO_OUTLINE,
                        size=12,
                        color=UIConfig.COLOR_INFO,
                        tooltip=(
                            "Runs automatically after each successful build.\n"
                            "Required packages are merged into the install list.\n"
                            "Command runs with shell=True, 30s timeout."
                        ),
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            post_build_command_field,
            post_build_packages_field,
            ft.Divider(height=4, color=colors.get("section_border")),
            _section_header(
                "Templates",
                "Custom boilerplate and folder structure overrides",
            ),
            templates_path_row,
            ft.Text(
                "Leave empty to use default location. "
                "Files saved here override bundled templates.",
                size=11,
                italic=True,
                color=colors.get("caption"),
            ),
        ],
        tight=True,
        spacing=6,
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=_create_dialog_title("Settings", colors, icon=ft.Icons.SETTINGS),
        content=ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=left_col, width=col_width),
                    ft.VerticalDivider(width=1, color=colors.get("section_border")),
                    ft.Container(content=right_col, width=col_width),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            width=col_width * 2 + 33 + 2 * UIConfig.DIALOG_CONTENT_PADDING,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=_create_dialog_actions(
            "Save",
            on_save_click,
            on_close_callback,
            ft.Icons.SAVE,
            is_dark_mode,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    return dialog


def create_history_dialog(
    entries: list,
    on_restore_callback: collections.abc.Callable,
    on_close_callback: collections.abc.Callable,
    on_clear_callback: collections.abc.Callable,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create a dialog showing recent project history.

    Args:
        entries: List of ProjectHistoryEntry objects, newest first.
        on_restore_callback: Callback receiving the selected entry on restore.
        on_close_callback: Callback when Cancel is clicked or dialog dismissed.
        on_clear_callback: Callback to clear all history entries.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog for browsing and restoring recent projects.
    """
    colors = get_theme_colors(is_dark_mode)
    selected_index: dict[str, int | None] = {"value": None}

    row_containers: list[ft.Container] = []

    def _highlight(idx: int) -> None:
        for i, container in enumerate(row_containers):
            if i == idx:
                container.bgcolor = (
                    ft.Colors.BLUE_900 if is_dark_mode else ft.Colors.BLUE_100
                )
                container.border = ft.Border.all(1, ft.Colors.BLUE_400)
            else:
                container.bgcolor = None
                container.border = ft.Border.all(
                    1, ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
                )

    def _on_row_click(idx: int):
        def handler(_):
            selected_index["value"] = idx
            _highlight(idx)
            restore_btn.disabled = False
            for c in row_containers:
                c.update()
            restore_btn.update()

        return handler

    def _on_restore(_):
        idx = selected_index["value"]
        if idx is not None and idx < len(entries):
            on_restore_callback(entries[idx])

    restore_btn = ft.FilledButton(
        "Restore",
        icon=ft.Icons.RESTORE,
        disabled=True,
        on_click=_on_restore,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_600,
                ft.ControlState.FOCUSED: ft.Colors.BLUE_400,
                ft.ControlState.HOVERED: ft.Colors.BLUE_500,
                ft.ControlState.PRESSED: ft.Colors.BLUE_700,
                ft.ControlState.DISABLED: ft.Colors.GREY_700,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
            },
        ),
    )

    if not entries:
        content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.HISTORY,
                        size=48,
                        color=ft.Colors.GREY_500,
                    ),
                    ft.Text(
                        "No recent projects",
                        size=16,
                        color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Projects will appear here after a successful build.",
                        size=13,
                        color=ft.Colors.GREY_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            width=500,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        )
    else:
        for i, entry in enumerate(entries):
            badge_row = _build_badge_row(entry)

            # Parse built_at for display
            try:
                dt = __import__("datetime").datetime.fromisoformat(entry.built_at)
                time_str = dt.strftime("%b %d, %H:%M")
            except (ValueError, AttributeError):
                time_str = entry.built_at[:16] if entry.built_at else ""

            row = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    entry.project_name,
                                    weight=ft.FontWeight.W_600,
                                    size=14,
                                    color=colors["main_title"],
                                    expand=True,
                                ),
                                ft.Text(
                                    time_str,
                                    size=11,
                                    color=ft.Colors.GREY_500,
                                ),
                            ],
                        ),
                        ft.Text(
                            entry.project_path,
                            size=12,
                            color=ft.Colors.GREY_500,
                        ),
                        ft.Row(badge_row, spacing=6) if badge_row else ft.Container(),
                    ],
                    spacing=2,
                    tight=True,
                ),
                border=ft.Border.all(
                    1, ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
                ),
                border_radius=6,
                padding=10,
                on_click=_on_row_click(i),
                ink=True,
            )
            row_containers.append(row)

        content = ft.Container(
            content=ft.Column(
                row_containers,
                spacing=6,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=500,
            height=min(len(entries) * 90, 400),
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        )

    cancel_bg_focused = ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
    cancel_btn = ft.OutlinedButton(
        "Cancel",
        on_click=on_close_callback,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                ft.ControlState.FOCUSED: cancel_bg_focused,
                ft.ControlState.HOVERED: cancel_bg_focused,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.GREY_500),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
            },
        ),
    )

    actions = [restore_btn, cancel_btn] if entries else [cancel_btn]
    if entries:
        clear_btn = ft.TextButton(
            "Clear History",
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=on_clear_callback,
            style=ft.ButtonStyle(color=ft.Colors.RED_400),
        )
        actions.insert(0, clear_btn)

    dialog = ft.AlertDialog(
        modal=True,
        title=_create_dialog_title("Recent Projects", colors, icon=ft.Icons.HISTORY),
        content=content,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )

    return dialog


def create_presets_dialog(
    presets: list,
    on_apply_callback: collections.abc.Callable,
    on_save_callback: collections.abc.Callable,
    on_close_callback: collections.abc.Callable,
    on_delete_callback: collections.abc.Callable,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create a dialog for managing project presets.

    The dialog has two sections: a save field at the top for saving
    the current configuration as a named preset, and a scrollable list
    of existing presets below that can be selected, applied, or deleted.

    Args:
        presets: List of ProjectPreset objects, newest first.
        on_apply_callback: Callback receiving the selected preset on apply.
        on_save_callback: Callback receiving the preset name string on save.
        on_close_callback: Callback when Cancel is clicked or dialog dismissed.
        on_delete_callback: Callback receiving the selected preset on delete.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog for managing project presets.
    """
    colors = get_theme_colors(is_dark_mode)
    selected_index: dict[str, int | None] = {"value": None}
    row_containers: list[ft.Container] = []

    # Empty state widget — shown when all presets are deleted
    empty_state = ft.Column(
        [
            ft.Icon(ft.Icons.BOOKMARK_OUTLINE, size=48, color=ft.Colors.GREY_500),
            ft.Text(
                "No saved presets",
                size=16,
                color=ft.Colors.GREY_500,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Save your current configuration using the field above.",
                size=13,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    # The scrollable column that holds preset rows (or empty state).
    # Keeping a reference lets _on_delete swap content in-place.
    list_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    def _highlight(idx: int) -> None:
        for i, container in enumerate(row_containers):
            if i == idx:
                container.bgcolor = (
                    ft.Colors.BLUE_900 if is_dark_mode else ft.Colors.BLUE_100
                )
                container.border = ft.Border.all(1, ft.Colors.BLUE_400)
            else:
                container.bgcolor = None
                container.border = ft.Border.all(
                    1, ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
                )

    def _on_row_click(idx: int):
        def handler(_):
            selected_index["value"] = idx
            _highlight(idx)
            apply_btn.disabled = False
            # Disable delete for built-in presets
            delete_btn.disabled = getattr(presets[idx], "builtin", False)
            for c in row_containers:
                c.update()
            apply_btn.update()
            delete_btn.update()

        return handler

    def _on_apply(_):
        idx = selected_index["value"]
        if idx is not None and idx < len(presets):
            on_apply_callback(presets[idx])

    def _on_delete(_):
        """Remove the selected preset and update the list in-place.

        Flet pattern: mutate the Column's .controls list, then call
        .update() on it — the UI re-renders without closing the dialog.
        """
        idx = selected_index["value"]
        if idx is None or idx >= len(presets):
            return

        # Built-in presets cannot be deleted
        if getattr(presets[idx], "builtin", False):
            return

        # Persist deletion via the callback
        on_delete_callback(presets[idx])

        # Remove from data and UI
        presets.pop(idx)
        row_containers.pop(idx)

        # Reassign on_click handlers so indices stay correct
        for new_idx, container in enumerate(row_containers):
            container.on_click = _on_row_click(new_idx)

        # Reset selection
        selected_index["value"] = None
        apply_btn.disabled = True
        delete_btn.disabled = True

        if row_containers:
            # Update the column with remaining rows
            list_column.controls = list(row_containers)
            list_container.height = min(len(row_containers) * 80, 320)
        else:
            # Swap to empty state — replace the column content
            list_column.controls = [empty_state]
            list_column.scroll = None
            list_container.height = None
            # Hide action buttons when no presets remain
            apply_btn.visible = False
            delete_btn.visible = False

        list_container.update()
        apply_btn.update()
        delete_btn.update()

    def _on_save(_):
        name = name_field.value.strip() if name_field.value else ""
        if name:
            on_save_callback(name)

    # Save section
    name_field = ft.TextField(
        hint_text="Preset name...",
        expand=True,
        border_color=ft.Colors.GREY_600,
        focused_border_color=ft.Colors.BLUE_400,
        on_submit=_on_save,
    )
    save_btn = ft.FilledButton(
        "Save Current",
        icon=ft.Icons.SAVE_OUTLINED,
        on_click=_on_save,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.GREEN_700,
                ft.ControlState.HOVERED: ft.Colors.GREEN_600,
                ft.ControlState.PRESSED: ft.Colors.GREEN_800,
            },
        ),
    )
    save_section = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Save current configuration as a preset:",
                    size=13,
                    color=ft.Colors.GREY_400 if is_dark_mode else ft.Colors.GREY_600,
                ),
                ft.Row([name_field, save_btn], spacing=8),
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.Padding(left=0, top=0, right=0, bottom=12),
        border=ft.Border(
            bottom=ft.BorderSide(
                1, ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
            )
        ),
    )

    # Action buttons
    apply_btn = ft.FilledButton(
        "Apply",
        icon=ft.Icons.CHECK,
        disabled=True,
        on_click=_on_apply,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_600,
                ft.ControlState.FOCUSED: ft.Colors.BLUE_400,
                ft.ControlState.HOVERED: ft.Colors.BLUE_500,
                ft.ControlState.PRESSED: ft.Colors.BLUE_700,
                ft.ControlState.DISABLED: ft.Colors.GREY_700,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
            },
        ),
    )
    delete_btn = ft.TextButton(
        "Delete",
        icon=ft.Icons.DELETE_OUTLINE,
        disabled=True,
        on_click=_on_delete,
        style=ft.ButtonStyle(color=ft.Colors.RED_400),
    )

    # Preset list
    if not presets:
        list_column.controls = [empty_state]
        list_column.scroll = None
    else:
        for i, preset in enumerate(presets):
            badge_row = _build_badge_row(preset, include_dev=True)

            # Parse saved_at for display
            try:
                dt = __import__("datetime").datetime.fromisoformat(preset.saved_at)
                time_str = dt.strftime("%b %d, %H:%M")
            except (ValueError, AttributeError):
                time_str = preset.saved_at[:16] if preset.saved_at else ""

            # Build details line
            details = []
            if preset.python_version:
                details.append(f"Python {preset.python_version}")
            if preset.git_enabled:
                details.append("Git")
            if preset.include_starter_files:
                details.append("Starter files")
            details_text = " · ".join(details)

            # Build name row with optional "Built-in" badge
            name_row_controls: list[ft.Control] = [
                ft.Text(
                    preset.name,
                    weight=ft.FontWeight.W_600,
                    size=14,
                    color=colors["main_title"],
                    expand=True,
                ),
            ]
            if getattr(preset, "builtin", False):
                name_row_controls.append(
                    ft.Container(
                        content=ft.Text("Built-in", size=10, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.TEAL_700,
                        border_radius=4,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    )
                )
            name_row_controls.append(
                ft.Text(
                    time_str,
                    size=11,
                    color=ft.Colors.GREY_500,
                ),
            )

            row = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(name_row_controls),
                        ft.Text(
                            details_text,
                            size=12,
                            color=ft.Colors.GREY_500,
                        ),
                        ft.Row(badge_row, spacing=6) if badge_row else ft.Container(),
                    ],
                    spacing=2,
                    tight=True,
                ),
                border=ft.Border.all(
                    1, ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
                ),
                border_radius=6,
                padding=10,
                on_click=_on_row_click(i),
                ink=True,
            )
            row_containers.append(row)

        list_column.controls = list(row_containers)

    # Wrap list_column in a container so we can adjust height on delete
    list_container = ft.Container(
        content=list_column,
        height=min(len(presets) * 80, 320) if presets else None,
        padding=ft.Padding(left=0, top=20, right=0, bottom=20) if not presets else None,
    )

    content = ft.Container(
        content=ft.Column(
            [save_section, list_container],
            spacing=12,
            tight=True,
        ),
        width=500,
        padding=UIConfig.DIALOG_CONTENT_PADDING,
    )

    cancel_bg_focused = ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
    cancel_btn = ft.OutlinedButton(
        "Cancel",
        on_click=on_close_callback,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                ft.ControlState.FOCUSED: cancel_bg_focused,
                ft.ControlState.HOVERED: cancel_bg_focused,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.GREY_500),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
            },
        ),
    )

    actions = [delete_btn, apply_btn, cancel_btn] if presets else [cancel_btn]

    return ft.AlertDialog(
        modal=True,
        title=_create_dialog_title("Presets", colors, icon=ft.Icons.BOOKMARK_OUTLINE),
        content=content,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )


def create_file_editor_view(
    filename: str,
    initial_content: str,
    on_save: collections.abc.Callable[[str], None],
    on_reset: collections.abc.Callable[[], None],
    on_close: collections.abc.Callable,
    is_dark_mode: bool,
    has_override: bool = False,
    has_user_template: bool = False,
    user_template_path: str | None = None,
) -> ft.View:
    """Create a full-screen View with an enhanced code editor for editing file content.

    Uses a pushed View instead of a modal AlertDialog so that snackbars
    (e.g. ruff lint errors on save) render correctly above the editor.

    Args:
        filename: Name of the file being edited (e.g., "main.py").
        initial_content: Content to populate the editor with.
        on_save: Callback receiving the edited content string.
        on_reset: Callback to reset file to boilerplate default.
        on_close: Callback when the editor view is closed (Cancel / close button).
        is_dark_mode: Whether dark mode is active.
        has_override: Whether this file already has a custom override.
        has_user_template: Whether a user template file exists for this file.
        user_template_path: Full path to the user template file (for title bar
            display and built-in Save). Falls back to bare filename if None.

    Returns:
        Configured ft.View containing an EnhancedCodeEditor.
    """
    import asyncio
    from contextlib import suppress

    import flet_code_editor as fce
    from fce_enhanced import EnhancedCodeEditor
    from fce_enhanced.languages import language_for_path

    target_lang = language_for_path(filename)

    # register_keyboard_shortcuts=False so the app's keyboard handler
    # can forward shortcuts to the editor (and handle Escape to close).
    editor = EnhancedCodeEditor(
        value=initial_content,
        language=target_lang,
        register_keyboard_shortcuts=False,
        expand=True,
    )

    # The underlying fce.CodeEditor doesn't apply syntax highlighting on its
    # initial render — it requires a language toggle (set dummy → flush → set
    # real) to trigger a full re-render with colors.  Hook into did_mount to
    # perform this toggle once the control is in the widget tree.
    _original_did_mount = editor.did_mount

    def _did_mount_with_highlight():
        _original_did_mount()
        dummy_lang = (
            fce.CodeLanguage.PLAINTEXT
            if target_lang != fce.CodeLanguage.PLAINTEXT
            else fce.CodeLanguage.PYTHON
        )
        editor._code_editor.language = dummy_lang
        with suppress(RuntimeError):
            editor._code_editor.update()

        async def _apply_real_lang():
            await asyncio.sleep(0.05)
            editor._code_editor.language = target_lang
            with suppress(RuntimeError):
                editor.update()

        asyncio.create_task(_apply_real_lang())

    editor.did_mount = _did_mount_with_highlight

    # Set _current_path so the title bar persists through edits (dirty state)
    # and so built-in Save (Cmd+S) writes to the correct location.
    editor._current_path = user_template_path or filename
    if user_template_path:
        try:
            display = "~/" + str(Path(user_template_path).relative_to(Path.home()))
        except ValueError:
            display = user_template_path
        editor._title_bar.value = display
    else:
        editor._title_bar.value = filename

    def handle_save(_):
        on_save(editor.value)

    save_btn = ft.TextButton(
        "Save",
        icon=ft.Icons.SAVE,
        on_click=handle_save,
    )
    reset_btn = ft.TextButton(
        "Reset to Default",
        icon=ft.Icons.RESTART_ALT,
        on_click=lambda _: on_reset(),
        disabled=not (has_override or has_user_template),
    )
    cancel_btn = ft.TextButton("Cancel", on_click=lambda _: on_close())

    view = ft.View(
        route="/editor",
        controls=[
            ft.AppBar(
                leading=ft.Icon(ft.Icons.EDIT, size=16),
                title=ft.Text(f"Edit: {filename}", size=14),
                toolbar_height=36,
                actions=[
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_size=18,
                        tooltip="Close Editor (Esc)",
                        on_click=lambda _: on_close(),
                    ),
                ],
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        editor,
                        ft.Row(
                            controls=[reset_btn, save_btn, cancel_btn],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                width=880,
                alignment=ft.Alignment(0, 0),
                expand=True,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                margin=ft.margin.only(bottom=12),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        padding=0,
    )
    # Expose the editor on the view so handlers can access it for keyboard shortcuts.
    view.editor = editor
    return view


def create_import_tree_dialog(
    on_import_callback,
    on_close_callback,
    is_dark_mode: bool,
) -> ft.AlertDialog:
    """Create dialog for importing a text tree structure into App Subfolders.

    Users paste a tree structure (box-drawing or plain indented) and the parser
    converts it into folder/file dicts. Supports Replace or Merge modes.

    Args:
        on_import_callback: Callback(folders: list[dict], root_files: list[str],
            mode: str) called with parsed folder dicts, root-level files,
            and "replace" or "merge".
        on_close_callback: Callback when Cancel is clicked.
        is_dark_mode: Whether dark mode is active.

    Returns:
        Configured AlertDialog for importing tree structures.
    """
    from uv_forger.core.tree_parser import parse_tree_text_full

    colors = get_theme_colors(is_dark_mode)

    warning_text = ft.Text(
        value="",
        color=UIConfig.COLOR_WARNING,
        size=13,
        visible=False,
        weight=ft.FontWeight.W_500,
    )

    preview_text = ft.Text(
        value="",
        size=13,
        visible=False,
        weight=ft.FontWeight.W_500,
    )

    tree_field = ft.TextField(
        label="Tree structure",
        hint_text=(
            "Paste a project tree here, e.g.:\n"
            "├── core/\n"
            "│   ├── __init__.py\n"
            "│   └── state.py\n"
            "├── ui/\n"
            "│   └── components.py\n"
            "└── utils/"
        ),
        multiline=True,
        min_lines=10,
        max_lines=16,
        width=480,
        autofocus=True,
        text_style=ft.TextStyle(font_family="monospace"),
    )

    mode_radio = ft.RadioGroup(
        value="replace",
        content=ft.Row(
            [
                ft.Radio(value="replace", label="Replace current folders"),
                ft.Radio(value="merge", label="Merge with current"),
            ],
            spacing=16,
        ),
    )

    # State for parsed result (mutable containers for closure)
    parsed_result: list[list[dict]] = [[]]  # folders
    parsed_root_files: list[list[str]] = [[]]  # root-level files

    def _count_recursive(folders: list[dict]) -> tuple[int, int]:
        """Count total folders and files recursively."""
        folder_count = 0
        file_count = 0
        for f in folders:
            folder_count += 1
            file_count += len(f.get("files", []))
            if f.get("create_init"):
                file_count += 1
            sub = f.get("subfolders", [])
            if sub:
                sf, sfi = _count_recursive(sub)
                folder_count += sf
                file_count += sfi
        return folder_count, file_count

    def on_preview_click(e):
        raw = tree_field.value or ""
        if not raw.strip():
            warning_text.value = "Paste a tree structure first."
            warning_text.visible = True
            preview_text.visible = False
            import_button.disabled = True
            e.page.update()
            return

        try:
            result = parse_tree_text_full(raw)
        except Exception as exc:
            warning_text.value = f"Parse error: {exc}"
            warning_text.visible = True
            preview_text.visible = False
            import_button.disabled = True
            e.page.update()
            return

        if not result.folders and not result.root_files:
            warning_text.value = (
                "No folders found. Ensure folders have a trailing / "
                "and the structure is indented correctly."
            )
            warning_text.visible = True
            preview_text.visible = False
            import_button.disabled = True
            e.page.update()
            return

        parsed_result[0] = result.folders
        parsed_root_files[0] = result.root_files
        folder_count, file_count = _count_recursive(result.folders)
        top_names = ", ".join(f["name"] for f in result.folders[:5])
        if len(result.folders) > 5:
            top_names += f", ... (+{len(result.folders) - 5} more)"

        root_file_info = ""
        if result.root_files:
            root_file_info = (
                f", {len(result.root_files)} root file"
                f"{'s' if len(result.root_files) != 1 else ''}"
            )

        preview_text.value = (
            f"Parsed: {folder_count} folder{'s' if folder_count != 1 else ''}, "
            f"{file_count} file{'s' if file_count != 1 else ''}"
            f"{root_file_info}\n"
            f"Top-level: {top_names}"
        )
        preview_text.color = UIConfig.COLOR_SUCCESS
        preview_text.visible = True
        warning_text.visible = False
        import_button.disabled = False
        e.page.update()

    def on_import_click(e):
        if not parsed_result[0] and not parsed_root_files[0]:
            warning_text.value = "Click Preview first to parse the tree."
            warning_text.visible = True
            e.page.update()
            return
        on_import_callback(parsed_result[0], parsed_root_files[0], mode_radio.value)

    import_button = ft.FilledButton(
        "Import",
        icon=ft.Icons.DOWNLOAD,
        on_click=on_import_click,
        disabled=True,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_600,
                ft.ControlState.FOCUSED: ft.Colors.BLUE_400,
                ft.ControlState.HOVERED: ft.Colors.BLUE_500,
                ft.ControlState.PRESSED: ft.Colors.BLUE_700,
                ft.ControlState.DISABLED: ft.Colors.GREY_700,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
            },
        ),
    )

    cancel_bg_focused = ft.Colors.GREY_700 if is_dark_mode else ft.Colors.GREY_300
    cancel_button = ft.OutlinedButton(
        "Cancel",
        on_click=on_close_callback,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                ft.ControlState.FOCUSED: cancel_bg_focused,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.GREY_600),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.WHITE),
            },
        ),
    )

    preview_button = ft.Button(
        "Preview",
        icon=ft.Icons.VISIBILITY,
        on_click=on_preview_click,
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=_create_dialog_title(
            "Import Tree Structure", colors, icon=ft.Icons.ACCOUNT_TREE
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Paste a text tree structure below "
                        "(tree command output, README snippet, etc.).\n"
                        "Folders must end with /. "
                        "__init__.py entries set create_init on the parent.",
                        size=13,
                        color=colors.get("section_title"),
                    ),
                    ft.Container(height=4),
                    tree_field,
                    ft.Row([preview_button], spacing=8),
                    mode_radio,
                    warning_text,
                    preview_text,
                ],
                tight=True,
                spacing=8,
            ),
            width=520,
            padding=UIConfig.DIALOG_CONTENT_PADDING,
        ),
        actions=[import_button, cancel_button],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Expose for testing
    dialog.tree_field = tree_field
    dialog.mode_radio = mode_radio
    dialog.preview_button = preview_button
    dialog.import_button = import_button
    dialog.warning_text = warning_text
    dialog.preview_text = preview_text

    return dialog
