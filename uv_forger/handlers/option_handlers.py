"""Handlers for option checkboxes, framework/project type dialogs, and template loading."""

import flet as ft

from uv_forger.core.constants import (
    ALWAYS_DEV_PACKAGES,
    DEFAULT_FOLDERS,
    DEFAULT_PYTHON_VERSION,
    FRAMEWORK_PACKAGE_MAP,
    PROJECT_TYPE_PACKAGE_MAP,
)
from uv_forger.core.template_merger import merge_folder_lists, normalize_folder
from uv_forger.ui.dialog_data import (
    OTHER_PROJECT_CHECKBOX_LABEL,
    UI_PROJECT_CHECKBOX_LABEL,
)
from uv_forger.ui.dialogs import (
    create_framework_dialog,
)


class OptionHandlersMixin:
    """Mixin for option checkbox toggles, framework/project type dialogs,
    and template loading/merging.

    Expects HandlerBase helpers, folder/package display methods available via self.
    """

    # --- Simple Toggle Handlers ---

    def on_python_version_select(self, value: str) -> None:
        """Handle Python version selection from CustomDropdown."""
        self.state.python_version = value or DEFAULT_PYTHON_VERSION
        self._set_status(
            f"Python version set to {self.state.python_version}",
            "info",
            update=True,
        )

    async def on_git_toggle(self, e: ft.ControlEvent) -> None:
        """Handle git initialization checkbox toggle."""
        self.state.git_enabled = e.control.value
        self._style_selected_checkbox(e.control)
        status = "enabled" if self.state.git_enabled else "disabled"
        self._set_status(f"Git initialization {status}.", "info", update=True)

    async def on_boilerplate_toggle(self, e: ft.ControlEvent) -> None:
        """Handle include starter files checkbox toggle."""
        self.state.include_starter_files = e.control.value
        self._style_selected_checkbox(e.control)
        status = "enabled" if self.state.include_starter_files else "disabled"
        self._set_status(f"Starter files {status}.", "info", update=True)

    # --- UI Framework Dialog ---

    async def on_ui_project_toggle(self, e: ft.ControlEvent) -> None:
        """Handle UI project checkbox toggle.

        Always opens the framework selection dialog. The dialog callbacks
        determine the final checked/unchecked state. Clicking an already-checked
        checkbox reopens the dialog to allow changing the selection.
        """
        e.control.value = True
        self.state.ui_project_enabled = True
        self._style_selected_checkbox(e.control)
        self._show_framework_dialog()
        self.page.update()

    def _show_framework_dialog(self) -> None:
        """Show the UI framework selection dialog."""

        def on_select(framework: str | None) -> None:
            """Handle framework selection."""
            if framework is None:
                self.state.framework = None
                self.state.ui_project_enabled = False
                self.controls.ui_project_checkbox.value = False
                self.controls.ui_project_checkbox.label = UI_PROJECT_CHECKBOX_LABEL
                self._style_selected_checkbox(self.controls.ui_project_checkbox)
                self._reload_and_merge_templates()
                self._set_status("UI framework cleared.", "info", update=False)
            else:
                self.state.framework = framework
                self.controls.ui_project_checkbox.label = f"UI Framework: {framework}"
                self._style_selected_checkbox(self.controls.ui_project_checkbox)
                self._reload_and_merge_templates()
                self._set_status(
                    f"Framework set to {framework}. Template loaded.",
                    "success",
                    update=False,
                )

            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def on_close(_=None) -> None:
            """Handle dialog close/cancel."""
            if not self.state.framework:
                self.state.ui_project_enabled = False
                self.controls.ui_project_checkbox.value = False
                self.controls.ui_project_checkbox.label = UI_PROJECT_CHECKBOX_LABEL
                self._style_selected_checkbox(self.controls.ui_project_checkbox)
                self._set_status("No framework selected.", "info", update=False)

            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_framework_dialog(
            on_select_callback=on_select,
            on_close_callback=on_close,
            current_selection=self.state.framework,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = on_close
        self.page.update()

    # --- Project Type Dialog ---

    async def on_other_project_toggle(self, e: ft.ControlEvent) -> None:
        """Handle Other Project Type checkbox toggle.

        Always opens the project type selection dialog. The dialog callbacks
        determine the final checked/unchecked state. Clicking an already-checked
        checkbox reopens the dialog to allow changing the selection.
        """
        e.control.value = True
        self.state.other_project_enabled = True
        self._style_selected_checkbox(e.control)
        self._show_project_type_dialog()
        self.page.update()

    def _show_project_type_dialog(self) -> None:
        """Show the project type selection dialog."""
        from uv_forger.ui.dialogs import create_project_type_dialog

        def on_select(project_type: str | None) -> None:
            """Handle project type selection."""
            if project_type is None:
                self.state.project_type = None
                self.state.other_project_enabled = False
                self.controls.other_projects_checkbox.value = False
                self.controls.other_projects_checkbox.label = (
                    OTHER_PROJECT_CHECKBOX_LABEL
                )
                self._style_selected_checkbox(self.controls.other_projects_checkbox)
                self._reload_and_merge_templates()
                self._set_status("Project type cleared.", "info", update=False)
            else:
                self.state.project_type = project_type
                self._reload_and_merge_templates()

                type_name = project_type.replace("_", " ").title()
                self.controls.other_projects_checkbox.label = f"Project: {type_name}"
                self._style_selected_checkbox(self.controls.other_projects_checkbox)
                self._set_status(
                    f"Project Type: {type_name}. Template loaded.",
                    "success",
                    update=False,
                )

            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def on_close(_=None) -> None:
            """Handle dialog close/cancel."""
            if not self.state.project_type:
                self.state.other_project_enabled = False
                self.controls.other_projects_checkbox.value = False
                self.controls.other_projects_checkbox.label = (
                    OTHER_PROJECT_CHECKBOX_LABEL
                )
                self._style_selected_checkbox(self.controls.other_projects_checkbox)
                self._set_status("No project type selected.", "info", update=False)

            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_project_type_dialog(
            on_select_callback=on_select,
            on_close_callback=on_close,
            current_selection=self.state.project_type,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = on_close
        self.page.update()

    # --- Template Loading & Merging ---

    def _load_template_folders(self, template_name: str | None) -> list[dict]:
        """Load and normalize folder list from a template.

        Args:
            template_name: Template path (e.g. "flet", "project_types/django"),
                or None for default.

        Returns:
            List of normalized folder dicts.
        """
        settings = self.template_loader.load_config(template_name)
        raw_folders = settings.get("folders", DEFAULT_FOLDERS.copy())
        return [normalize_folder(folder) for folder in raw_folders]

    def _load_project_type_template(self, project_type: str | None) -> None:
        """Load folder template for the specified project type.

        Args:
            project_type: Project type key (e.g., "django"), or None for default.
        """
        template_name = f"project_types/{project_type}" if project_type else None
        self.state.folders = self._load_template_folders(template_name)
        self._update_folder_display()

    def _load_framework_template(self, framework: str | None) -> None:
        """Load folder template for the specified framework.

        Args:
            framework: UI framework name (e.g., "flet"), or None for default.
        """
        self.state.folders = self._load_template_folders(framework)
        self._update_folder_display()

    def _reload_and_merge_templates(self) -> None:
        """Reload templates based on current selections and merge if both are active.

        If both a UI framework and a project type are selected, their folder
        structures are merged. Otherwise the single active template is used.
        Falls back to the default template when neither is selected.
        """
        framework = self.state.framework if self.state.ui_project_enabled else None
        project_type = (
            self.state.project_type if self.state.other_project_enabled else None
        )

        if framework and project_type:
            fw_folders = self._load_template_folders(framework)
            pt_folders = self._load_template_folders(f"project_types/{project_type}")
            self.state.folders = merge_folder_lists(fw_folders, pt_folders)

            pt_name = project_type.replace("_", " ").title()
            self._set_status(
                f"Merged templates: {framework} + {pt_name}", "info", update=False
            )
        elif framework:
            self.state.folders = self._load_template_folders(framework)
        elif project_type:
            self.state.folders = self._load_template_folders(
                f"project_types/{project_type}"
            )
        else:
            self.state.folders = self._load_template_folders(None)

        # Clear selections and modification flag since structure was replaced
        self.state.folders_modified = False
        self.state.imported_structure = False
        self.state.root_files = []
        self.state.selected_item_path = None
        self.state.selected_item_type = None
        self.state.selected_package_idx = None

        # Rebuild package list: keep user-added packages, replace auto ones
        new_auto = self._collect_state_packages()
        prev_auto = set(self.state.auto_packages)
        manual = [pkg for pkg in self.state.packages if pkg not in prev_auto]
        new_auto_set = set(new_auto)
        self.state.packages = new_auto + [
            pkg for pkg in manual if pkg not in new_auto_set
        ]
        self.state.auto_packages = new_auto
        # Prune dev_packages to only include packages still in the list
        self.state.dev_packages &= set(self.state.packages)
        # Auto-mark always-dev packages
        self.state.dev_packages |= ALWAYS_DEV_PACKAGES & set(self.state.packages)

        self._update_folder_display()
        self._update_package_display()

    def _collect_state_packages(self) -> list[str]:
        """Build the package list from current framework/project type selections.

        Includes post-build required packages when the post-build command is
        enabled in settings.

        Returns:
            List of package name strings derived from the active selections.
        """
        packages: list[str] = []
        if self.state.ui_project_enabled and self.state.framework:
            fw_pkg = FRAMEWORK_PACKAGE_MAP.get(self.state.framework)
            if fw_pkg:
                packages.append(fw_pkg)
        if self.state.other_project_enabled and self.state.project_type:
            packages.extend(PROJECT_TYPE_PACKAGE_MAP.get(self.state.project_type, []))
        if self.state.settings.post_build_command_enabled:
            extra = self.state.settings.post_build_packages
            if extra:
                existing = {p.lower() for p in packages}
                for pkg in (p.strip() for p in extra.split(",")):
                    if pkg and pkg.lower() not in existing:
                        packages.append(pkg)
        return packages
