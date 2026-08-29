"""Event handlers for UV Forger.

This module composes handler mixins into a single Handlers class and
provides the attach_handlers() function that wires all UI controls.
"""

import flet as ft

from uv_forger.core.settings_manager import get_user_templates_dir
from uv_forger.core.state import AppState
from uv_forger.core.template_loader import TemplateLoader
from uv_forger.handlers.build_handlers import BuildHandlersMixin
from uv_forger.handlers.feature_handlers import FeatureHandlersMixin
from uv_forger.handlers.folder_handlers import FolderHandlersMixin
from uv_forger.handlers.handler_base import HandlerBase, wrap_async
from uv_forger.handlers.input_handlers import InputHandlersMixin
from uv_forger.handlers.option_handlers import OptionHandlersMixin
from uv_forger.handlers.package_handlers import PackageHandlersMixin
from uv_forger.ui.components import Controls


def _get_controls(page: ft.Page) -> Controls:
    """Retrieve the Controls instance from the page."""
    return page.controls_ref


class Handlers(
    HandlerBase,
    InputHandlersMixin,
    OptionHandlersMixin,
    FolderHandlersMixin,
    PackageHandlersMixin,
    BuildHandlersMixin,
    FeatureHandlersMixin,
):
    """Event handlers for UI controls.

    Composes all handler mixins and provides shared state access.
    """

    def __init__(self, page: ft.Page, controls: Controls, state: AppState) -> None:
        """Initialize handler with page, controls, and state references.

        Args:
            page: The Flet page containing the UI controls.
            controls: Controls instance with references to interactive UI elements.
            state: The application state instance.
        """
        self.page = page
        self.controls = controls
        self.state = state
        self.template_loader = TemplateLoader(
            user_templates_dir=get_user_templates_dir(state.settings),
        )


def attach_handlers(page: ft.Page, state: AppState) -> None:
    """Attach event handlers to UI controls.

    Args:
        page: The Flet page containing the UI controls.
        state: The application state instance for handlers to access.
    """
    controls = _get_controls(page)
    handlers = Handlers(page, controls, state)

    # Load default folder template and package list on startup
    handlers._reload_and_merge_templates()
    handlers._update_metadata_summary()

    # Set initial UI state (path icon if default path exists, button disabled)
    if state.path_valid:
        handlers._set_validation_icon(controls.project_path_input, True)
    handlers._update_build_button_state()

    # Apply green styling to any checkboxes that start in a checked state
    for checkbox in (
        controls.create_git_checkbox,
        controls.include_starter_files_checkbox,
    ):
        handlers._style_selected_checkbox(checkbox)

    # --- Path & Name Handlers ---
    controls.copy_path_button.on_click = wrap_async(handlers.on_copy_path)
    controls.browse_button.on_click = wrap_async(handlers.on_browse_click)
    controls.project_path_input.on_change = wrap_async(handlers.on_path_change)
    controls.project_name_input.on_change = wrap_async(handlers.on_project_name_change)
    controls.check_pypi_button.on_click = wrap_async(handlers.on_check_pypi)

    # --- Options Handlers ---
    controls.python_version_dropdown.on_select = handlers.on_python_version_select
    controls.preset_dropdown.on_select = handlers.on_preset_quick_select
    controls.create_git_checkbox.on_change = wrap_async(handlers.on_git_toggle)
    controls.include_starter_files_checkbox.on_change = wrap_async(
        handlers.on_boilerplate_toggle
    )
    controls.ui_project_checkbox.on_change = wrap_async(handlers.on_ui_project_toggle)
    controls.other_projects_checkbox.on_change = wrap_async(
        handlers.on_other_project_toggle
    )

    # --- Folder Management Handlers ---
    controls.add_folder_button.on_click = wrap_async(handlers.on_add_folder)
    controls.remove_folder_button.on_click = wrap_async(handlers.on_remove_folder)
    controls.edit_file_button.on_click = wrap_async(handlers.on_edit_file)
    controls.save_as_preset_button.on_click = wrap_async(handlers.on_presets_click)
    controls.import_tree_button.on_click = wrap_async(handlers.on_import_tree)
    controls.clear_folders_button.on_click = wrap_async(handlers.on_clear_folders)

    # --- Package Management Handlers ---
    # PackagesPanel is built before handlers exist, so it dispatches clicks
    # through this slot on Controls.
    controls.on_package_select = handlers._on_package_select
    # FoldersPanel likewise dispatches through the callbacks object
    # build_main_view created for it.
    controls.folder_callbacks.select = handlers._on_item_select
    controls.folder_callbacks.file_action = handlers._on_file_context_action
    controls.folder_callbacks.folder_action = handlers._on_folder_context_action
    controls.add_package_button.on_click = wrap_async(handlers.on_add_package)
    controls.remove_package_button.on_click = wrap_async(handlers.on_remove_package)
    controls.clear_packages_button.on_click = wrap_async(handlers.on_clear_packages)
    controls.toggle_dev_button.on_click = wrap_async(handlers.on_toggle_dev)

    # --- Main Action Handlers ---
    controls.build_project_button.on_click = wrap_async(handlers.on_build_project)
    controls.reset_button.on_click = wrap_async(handlers.on_reset)
    controls.exit_button.on_click = wrap_async(handlers.on_exit)

    # --- UI Feature Handlers ---
    controls.app_cheat_sheet_menu_item.on_click = wrap_async(
        handlers.on_app_cheat_sheet_click
    )
    controls.history_menu_item.on_click = wrap_async(handlers.on_history_click)
    controls.presets_menu_item.on_click = wrap_async(handlers.on_presets_click)
    controls.log_viewer_menu_item.on_click = wrap_async(handlers.on_log_viewer_click)
    controls.metadata_checkbox.on_change = wrap_async(handlers.on_metadata_toggle)
    controls.settings_menu_item.on_click = wrap_async(handlers.on_settings_click)
    controls.help_menu_item.on_click = wrap_async(handlers.on_help_click)
    controls.about_menu_item.on_click = wrap_async(handlers.on_about_click)
    controls.theme_toggle_button.on_click = wrap_async(handlers.on_theme_toggle)

    # --- Keyboard Shortcuts ---
    page.on_keyboard_event = wrap_async(handlers.on_keyboard_event)

    # Update page to register all handlers
    page.update()
