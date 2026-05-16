"""Handlers for theme toggle, help dialog, about dialog, settings, and log viewer."""

import asyncio
import subprocess
from datetime import date
from pathlib import Path

import flet as ft

from uv_forger.core.constants import (
    ABOUT_FILE,
    APP_CHEAT_SHEET_FILE,
    HELP_FILE,
    LOG_DIR,
    SUPPORTED_IDES,
)
from uv_forger.core.history_manager import clear_history, load_history
from uv_forger.core.preset_manager import delete_preset, load_presets
from uv_forger.core.settings_manager import get_user_templates_dir, save_settings
from uv_forger.ui.content_dialogs import (
    create_about_dialog,
    create_app_cheat_sheet_dialog,
    create_help_dialog,
)
from uv_forger.ui.dialogs import (
    create_history_dialog,
    create_log_viewer_dialog,
    create_metadata_dialog,
    create_presets_dialog,
    create_settings_dialog,
)
from uv_forger.ui.theme_manager import get_theme_colors

# Parent of the app package — used to resolve module paths to source files
_APP_ROOT = Path(__file__).parent.parent.parent


class FeatureHandlersMixin:
    """Mixin for UI feature handlers: theme, help, about, settings, log viewer.

    Expects HandlerBase helpers available via self.
    """

    async def on_theme_toggle(self, e: ft.ControlEvent) -> None:
        """Handle theme toggle button click."""
        self.state.is_dark_mode = not self.state.is_dark_mode
        colors = get_theme_colors(self.state.is_dark_mode)

        if self.state.is_dark_mode:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.controls.theme_toggle_button.icon = ft.Icons.LIGHT_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.controls.theme_toggle_button.icon = ft.Icons.DARK_MODE

        for title_text in self.controls.section_titles:
            title_text.color = colors["section_title"]
        for container in self.controls.section_containers:
            container.border = ft.Border.all(1, colors["section_border"])

        self.page.bottom_appbar.bgcolor = colors["bottom_bar"]
        self.page.update()

    async def _open_markdown_dialog(
        self,
        doc_file: Path,
        fallback_content: str,
        error_prefix: str,
        dialog_factory,
        link_targets: dict[str, str],
    ) -> None:
        """Open a markdown-content dialog with internal-link routing.

        Args:
            doc_file: Path to the markdown file to display.
            fallback_content: Content shown when the file cannot be read.
            error_prefix: Prefix for the status error message on read failure.
            dialog_factory: Callable that builds the dialog (content, close_fn, page, dark_mode, on_internal_link).
            link_targets: Maps app:// path strings to handler method names on self.
        """
        try:
            content = doc_file.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as exc:
            content = fallback_content
            self._set_status(f"{error_prefix} ({exc})", "error", update=False)

        def close_dialog(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def handle_internal_link(path: str) -> None:
            close_dialog()
            handler_name = link_targets.get(path)
            if handler_name:
                asyncio.create_task(getattr(self, handler_name)(None))

        dialog = dialog_factory(
            content,
            close_dialog,
            self.page,
            self.state.is_dark_mode,
            on_internal_link=handle_internal_link,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    async def on_help_click(self, e: ft.ControlEvent) -> None:
        """Handle Help button click."""
        await self._open_markdown_dialog(
            HELP_FILE,
            "# UV Forger Help\n\n**Error**: Could not load help file.\n\n"
            "This application helps you create new Python projects using UV.\n\n"
            "For more information, visit: https://docs.astral.sh/uv/\n",
            "Warning: Help file not found",
            create_help_dialog,
            {"about": "on_about_click", "app-cheat-sheet": "on_app_cheat_sheet_click"},
        )

    async def on_app_cheat_sheet_click(self, e: ft.ControlEvent) -> None:
        """Handle App Cheat Sheet button click."""
        await self._open_markdown_dialog(
            APP_CHEAT_SHEET_FILE,
            "# App Cheat Sheet\n\nError: Could not load cheat sheet file.",
            "Warning: Cheat sheet file not found",
            create_app_cheat_sheet_dialog,
            {"help": "on_help_click", "about": "on_about_click"},
        )

    async def on_about_click(self, e: ft.ControlEvent) -> None:
        """Handle About button click.

        Internal links (app://help, app://app-cheat-sheet) close the About
        dialog and open the corresponding dialog directly.
        """
        await self._open_markdown_dialog(
            ABOUT_FILE,
            "# UV Forger\n\nError: Could not load about file.",
            "Warning: About file not found",
            create_about_dialog,
            {"help": "on_help_click", "app-cheat-sheet": "on_app_cheat_sheet_click"},
        )

    # URL schemes for IDEs that support file:line navigation.
    # More reliable than CLI commands which may not be on PATH.
    _IDE_URL_SCHEMES: dict[str, str] = {
        "VS Code": "vscode://file{path}:{line}",
        "Cursor": "cursor://file{path}:{line}",
        "Zed": "zed://file{path}:{line}",
    }

    def _open_file_in_ide(self, module_path: str, line_no: int) -> None:
        """Open a source file in the user's preferred IDE at a specific line.

        Resolves a dotted module path (e.g. ``app.core.state``) to a file
        under the ``app`` package directory and launches the IDE.  Uses URL schemes on
        macOS for reliability (CLI tools may not be on PATH); falls back
        to CLI commands on other platforms.

        Args:
            module_path: Dotted Python module path.
            line_no: Line number to jump to.
        """
        if module_path == "__main__":
            module_path = "uv_forger.main"
        rel = Path(module_path.replace(".", "/") + ".py")
        file_path = _APP_ROOT / rel
        if not file_path.is_file():
            return

        ide_name = self.state.settings.preferred_ide

        # Try URL scheme first (works on macOS without CLI in PATH)
        url_template = self._IDE_URL_SCHEMES.get(ide_name)
        if url_template:
            url = url_template.format(path=file_path, line=line_no)
            try:
                subprocess.Popen(["open", url])
                return
            except FileNotFoundError:
                pass

        # Fallback to CLI command
        command = SUPPORTED_IDES.get(ide_name)
        if command is None:
            command = self.state.settings.custom_ide_path
            if not command:
                return

        try:
            if ide_name == "PyCharm":
                subprocess.Popen([command, "--line", str(line_no), str(file_path)])
            else:
                subprocess.Popen([command, "--goto", f"{file_path}:{line_no}"])
        except FileNotFoundError:
            pass

    async def on_log_viewer_click(self, e: ft.ControlEvent) -> None:
        """Handle Log Viewer button click.

        Reads today's log file and displays it in a dialog with coloured,
        parsed log lines.  Location segments are clickable and open the
        source file in the user's preferred IDE.
        """
        log_file = LOG_DIR / f"app_{date.today()}.log"
        try:
            log_content = log_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._show_snackbar("No log file found for today", is_error=True)
            return
        except OSError as e:
            self._show_snackbar(f"Could not read log file: {e}", is_error=True)
            return

        def close_dialog(_=None):
            log_dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        log_dialog = create_log_viewer_dialog(
            log_content,
            close_dialog,
            self.state.is_dark_mode,
            on_location_click=self._open_file_in_ide,
        )

        self.page.overlay.append(log_dialog)
        log_dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    async def on_history_click(self, e: ft.ControlEvent) -> None:
        """Handle Recent Projects button click.

        Opens a dialog showing recent project builds. Selecting an entry
        and clicking Restore populates the UI with that project's config.
        """
        entries = load_history()

        def close_dialog(_=None):
            history_dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def on_restore(entry):
            close_dialog()
            self._restore_from_history(entry)

        def on_clear(_=None):
            clear_history()
            close_dialog()
            self._show_snackbar("History cleared")

        history_dialog = create_history_dialog(
            entries=entries,
            on_restore_callback=on_restore,
            on_close_callback=close_dialog,
            on_clear_callback=on_clear,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(history_dialog)
        history_dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    async def on_presets_click(self, e: ft.ControlEvent) -> None:
        """Handle Presets menu item click.

        Opens a dialog for saving the current configuration as a named
        preset, and for browsing/applying/deleting existing presets.
        """
        presets = load_presets()

        def close_dialog(_=None):
            presets_dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def on_apply(preset):
            close_dialog()
            self._apply_preset(preset)

        def on_save(name):
            self._save_current_as_preset(name)
            self._refresh_preset_dropdown()
            close_dialog()
            self._show_snackbar(f"Preset saved: {name}")

        def on_delete(preset):
            delete_preset(preset.name)
            self._refresh_preset_dropdown()

        presets_dialog = create_presets_dialog(
            presets=presets,
            on_apply_callback=on_apply,
            on_save_callback=on_save,
            on_close_callback=close_dialog,
            on_delete_callback=on_delete,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(presets_dialog)
        presets_dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    def _update_metadata_summary(self) -> None:
        """Update the metadata summary text next to the button."""
        parts = []
        if self.state.author_name:
            parts.append(self.state.author_name)
        if self.state.license_type:
            parts.append(self.state.license_type)
        self.controls.metadata_summary.value = " | ".join(parts) if parts else ""

    async def on_metadata_toggle(self, e: ft.ControlEvent) -> None:
        """Handle Project Metadata checkbox toggle.

        Always opens the metadata dialog. On save, keeps the checkbox checked.
        On cancel, restores the checkbox to its state before the dialog opened.
        """
        # on_change fires with the new value; capture what it was before the click
        prev_checked = not e.control.value
        save_called = [False]
        e.control.value = True
        self._style_selected_checkbox(e.control)
        self.page.update()

        def close_dialog(_=None):
            metadata_dialog.open = False
            self.state.active_dialog = None
            if not save_called[0]:
                # User cancelled — restore checkbox to pre-dialog state
                self.controls.metadata_checkbox.value = prev_checked
                self._style_selected_checkbox(self.controls.metadata_checkbox)
            self.page.update()

        def on_save(author_name, author_email, description, license_type):
            save_called[0] = True
            self.state.author_name = author_name
            self.state.author_email = author_email
            self.state.description = description
            self.state.license_type = license_type
            self._update_metadata_summary()
            close_dialog()
            self._show_snackbar("Metadata saved")

        metadata_dialog = create_metadata_dialog(
            state=self.state,
            on_save_callback=on_save,
            on_close_callback=close_dialog,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(metadata_dialog)
        metadata_dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()

    async def on_settings_click(self, e: ft.ControlEvent) -> None:
        """Handle Settings button click.

        Opens a dialog for editing user preferences (default paths, IDE,
        Python version, git default). Saves changes to disk and updates
        the live settings on the AppState.
        """

        def close_dialog(_=None):
            settings_dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        def on_save(updated_settings):
            old_templates_path = self.state.settings.custom_templates_path
            save_settings(updated_settings)
            self.state.settings = updated_settings
            # Rebuild template loader if templates path changed
            if updated_settings.custom_templates_path != old_templates_path:
                from uv_forger.core.template_loader import TemplateLoader

                self.template_loader = TemplateLoader(
                    user_templates_dir=get_user_templates_dir(updated_settings),
                )
            close_dialog()
            self._reload_and_merge_templates()
            self._show_snackbar("Settings saved")

        settings_dialog = create_settings_dialog(
            settings=self.state.settings,
            on_save_callback=on_save,
            on_close_callback=close_dialog,
            is_dark_mode=self.state.is_dark_mode,
        )

        self.page.overlay.append(settings_dialog)
        settings_dialog.open = True
        self.state.active_dialog = close_dialog
        self.page.update()
