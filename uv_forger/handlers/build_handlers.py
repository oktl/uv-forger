"""Handlers for build, reset, exit, and keyboard shortcuts."""

import subprocess
import sys
from pathlib import Path

import flet as ft
from loguru import logger

from uv_forger.core.async_executor import AsyncExecutor
from uv_forger.core.constants import (
    ALWAYS_DEV_PACKAGES,
    DEFAULT_FOLDERS,
    IDE_MACOS_APP_NAMES,
    SUPPORTED_IDES,
)
from uv_forger.core.history_manager import add_to_history, make_history_entry
from uv_forger.core.models import BuildSummaryConfig, ProjectConfig
from uv_forger.core.preset_manager import add_preset, load_presets, make_preset
from uv_forger.core.settings_manager import get_user_templates_dir
from uv_forger.core.template_merger import normalize_folder
from uv_forger.core.validator import validate_project_name
from uv_forger.handlers.git_handler import check_gh_authenticated, check_gh_available
from uv_forger.handlers.handler_base import wrap_async
from uv_forger.handlers.option_handlers import _append_post_build_packages
from uv_forger.handlers.project_builder import build_project
from uv_forger.ui.dialog_data import (
    OTHER_PROJECT_CHECKBOX_LABEL,
    UI_PROJECT_CHECKBOX_LABEL,
)
from uv_forger.ui.dialogs import (
    create_build_error_dialog,
    create_build_summary_dialog,
    create_confirm_dialog,
)


class BuildHandlersMixin:
    """Mixin for build execution, reset, exit, and keyboard shortcuts.

    Expects HandlerBase helpers and folder/template methods available via self.
    """

    @staticmethod
    def _open_in_file_manager(project_path: Path) -> None:
        """Open the project directory in the OS file manager.

        Args:
            project_path: Path to the project directory to open.
        """
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(project_path)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", str(project_path)])
        else:
            subprocess.Popen(["xdg-open", str(project_path)])

    @staticmethod
    def _open_in_terminal(project_path: Path) -> None:
        """Open a terminal window at the project root.

        Args:
            project_path: Path to the project directory to open in a terminal.
        """
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "Terminal", str(project_path)])
        elif sys.platform == "win32":
            subprocess.Popen(
                ["cmd"],
                cwd=str(project_path),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            for terminal, args in [
                ("gnome-terminal", [f"--working-directory={project_path}"]),
                ("konsole", ["--workdir", str(project_path)]),
                ("xfce4-terminal", ["--working-directory", str(project_path)]),
                ("xterm", []),
            ]:
                try:
                    subprocess.Popen([terminal] + args, cwd=str(project_path))
                    break
                except FileNotFoundError:
                    continue

    def _open_in_ide(self, project_path: Path) -> None:
        """Open the project directory in the user's preferred IDE.

        Uses the IDE configured in settings. Falls back to the CLI command
        from SUPPORTED_IDES, with macOS ``open -a`` handling for known apps.

        Args:
            project_path: Path to the project directory to open.
        """
        ide_name = self.state.settings.preferred_ide
        command = SUPPORTED_IDES.get(ide_name)

        # "Other / Custom" — use the custom path from settings
        if command is None:
            command = self.state.settings.custom_ide_path
            if not command:
                self._show_snackbar("No custom IDE path configured", is_error=True)
                return

        try:
            if sys.platform == "darwin" and ide_name in IDE_MACOS_APP_NAMES:
                subprocess.Popen(
                    ["open", "-a", IDE_MACOS_APP_NAMES[ide_name], str(project_path)]
                )
            elif sys.platform == "win32":
                # On Windows, IDE launchers like 'code' are .cmd batch scripts
                # and require shell=True to be resolved from PATH.
                subprocess.Popen([command, str(project_path)], shell=True)
            else:
                subprocess.Popen([command, str(project_path)])
        except FileNotFoundError:
            self._show_snackbar(f"{ide_name} not found", is_error=True)

    def _run_post_build_command(self, project_path: Path, command: str) -> None:
        """Run a user-configured command in the new project directory.

        Executes via the system shell with a 30-second timeout. Logs full
        output and shows a snackbar summary. Failures are logged but never
        block the remaining post-build actions.

        Args:
            project_path: Working directory for the command.
            command: Shell command string to execute.
        """
        if not command.strip():
            return

        logger.info("Running post-build command: {}", command)
        try:
            result = subprocess.run(
                command,
                cwd=str(project_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Post-build command succeeded: {}", result.stdout.strip())
                self._show_snackbar("Post-build command completed")
            else:
                logger.warning(
                    "Post-build command failed (exit {}): {}",
                    result.returncode,
                    result.stderr.strip(),
                )
                self._show_snackbar(
                    f"Post-build command failed (exit {result.returncode})",
                    is_error=True,
                )
        except subprocess.TimeoutExpired:
            logger.warning("Post-build command timed out after 30s: {}", command)
            self._show_snackbar("Post-build command timed out", is_error=True)
        except Exception as exc:
            logger.warning("Post-build command error: {}", exc)
            self._show_snackbar(f"Post-build command error: {exc}", is_error=True)

    async def _execute_build(
        self,
        open_folder: bool = False,
        open_ide: bool = False,
        open_terminal: bool = False,
        post_build_command: str = "",
        git_remote_mode: str | None = None,
    ) -> None:
        """Execute the project build after confirmation.

        Args:
            open_folder: Whether to open the project in the OS file manager after build.
            open_ide: Whether to open the project in the preferred IDE after build.
            open_terminal: Whether to open a terminal at the project root after build.
            post_build_command: Optional shell command to run in the project directory.
            git_remote_mode: Override for git remote mode (None = use settings default).
        """
        self.controls.progress_ring.visible = True
        self.controls.progress_bar.visible = True
        self.controls.progress_bar.value = 0
        self.controls.progress_step_text.visible = True
        self.controls.progress_step_text.value = ""
        self.controls.build_project_button.disabled = True
        self._set_status("Building project...", "info", update=True)

        config = ProjectConfig(
            project_name=self.state.project_name,
            project_path=Path(self.state.project_path),
            python_version=self.state.python_version,
            git_enabled=self.state.git_enabled,
            ui_project_enabled=self.state.ui_project_enabled,
            framework=self.state.framework or "",
            other_project_enabled=self.state.other_project_enabled,
            project_type=self.state.project_type,
            include_starter_files=self.state.include_starter_files,
            folders=self.state.folders
            if self.state.folders
            else DEFAULT_FOLDERS.copy(),
            packages=list(self.state.packages),
            dev_packages=list(self.state.dev_packages),
            file_overrides=dict(self.state.file_overrides),
            imported_structure=self.state.imported_structure,
            root_files=list(self.state.root_files),
            user_boilerplate_dir=get_user_templates_dir(self.state.settings)
            / "boilerplate",
            github_root=Path(self.state.settings.default_github_root),
            git_remote_mode=git_remote_mode or self.state.settings.git_remote_mode,
            github_username=self.state.settings.github_username,
            github_repo_private=self.state.settings.github_repo_private,
            author_name=self.state.author_name,
            author_email=self.state.author_email,
            description=self.state.description,
            license_type=self.state.license_type,
        )

        def _on_build_progress(msg: str, step: int, total: int) -> None:
            self.controls.progress_bar.value = step / total
            self.controls.progress_step_text.value = f"{step}/{total}"
            self._set_status(msg, "info", update=True)

        result = await AsyncExecutor.run(build_project, config, _on_build_progress)

        self.controls.progress_ring.visible = False
        self.controls.progress_bar.visible = False
        self.controls.progress_step_text.visible = False
        self._update_build_button_state()

        if result.success:
            self._set_status(result.message, "success", update=False)
            self._show_snackbar(result.message, is_error=False)

            # Save to recent projects history
            entry = make_history_entry(
                project_name=config.project_name,
                project_path=str(config.project_path),
                python_version=config.python_version,
                git_enabled=config.git_enabled,
                include_starter_files=config.include_starter_files,
                ui_project_enabled=config.ui_project_enabled,
                framework=config.framework or None,
                other_project_enabled=config.other_project_enabled,
                project_type=config.project_type,
                folders=config.folders,
                packages=config.packages,
                dev_packages=config.dev_packages,
                imported_structure=config.imported_structure,
                root_files=config.root_files,
            )
            add_to_history(entry)

            project_path = config.project_path / config.project_name
            if post_build_command:
                self._run_post_build_command(project_path, post_build_command)
            if open_folder:
                self._open_in_file_manager(project_path)
            if open_ide:
                self._open_in_ide(project_path)
            if open_terminal:
                self._open_in_terminal(project_path)
        else:
            self._set_status("Build failed. See error details.", "error", update=False)

            def close_error_dialog(_=None):
                error_dialog.open = False
                self.state.active_dialog = None
                self.page.update()

            error_dialog = create_build_error_dialog(
                error_message=result.message,
                on_close_callback=close_error_dialog,
                is_dark_mode=self.state.is_dark_mode,
            )
            self.page.overlay.append(error_dialog)
            error_dialog.open = True
            self.state.active_dialog = close_error_dialog

        self.page.update()

    def _apply_common_config(self, cfg) -> None:
        """Populate shared state and UI from a history entry or preset.

        Handles: python version, git, starter files, framework/project type,
        folders, packages, dev packages, post-build merge, checkbox sync.
        Does NOT touch name/path (history-only) or metadata (preset-only).
        """
        self.state.python_version = cfg.python_version
        self.state.git_enabled = cfg.git_enabled
        self.state.include_starter_files = cfg.include_starter_files
        self.state.ui_project_enabled = cfg.ui_project_enabled
        self.state.framework = cfg.framework
        self.state.other_project_enabled = cfg.other_project_enabled
        self.state.project_type = cfg.project_type
        self.state.folders = [normalize_folder(f) for f in cfg.folders]
        self.state.imported_structure = getattr(cfg, "imported_structure", False)
        self.state.root_files = list(getattr(cfg, "root_files", []))
        self.state.packages = list(cfg.packages)
        self.state.dev_packages = set(getattr(cfg, "dev_packages", []))
        _append_post_build_packages(self.state.packages, self.state.settings)
        self.state.auto_packages = list(self.state.packages)
        self.state.dev_packages = self.state.dev_packages | (
            ALWAYS_DEV_PACKAGES & set(self.state.packages)
        )

        self.controls.python_version_dropdown.value = cfg.python_version
        self.controls.create_git_checkbox.value = cfg.git_enabled
        self.controls.include_starter_files_checkbox.value = cfg.include_starter_files
        self.controls.ui_project_checkbox.value = cfg.ui_project_enabled
        self.controls.other_projects_checkbox.value = cfg.other_project_enabled

        if cfg.ui_project_enabled and cfg.framework:
            self.controls.ui_project_checkbox.label = f"UI Framework: {cfg.framework}"
        else:
            self.controls.ui_project_checkbox.label = UI_PROJECT_CHECKBOX_LABEL

        if cfg.other_project_enabled and cfg.project_type:
            self.controls.other_projects_checkbox.label = (
                f"Project Type: {cfg.project_type}"
            )
        else:
            self.controls.other_projects_checkbox.label = OTHER_PROJECT_CHECKBOX_LABEL

        for cb in (
            self.controls.create_git_checkbox,
            self.controls.include_starter_files_checkbox,
            self.controls.ui_project_checkbox,
            self.controls.other_projects_checkbox,
        ):
            self._style_selected_checkbox(cb)

        self._update_folder_display()
        self._update_package_display()
        self._update_build_button_state()

    def _restore_from_history(self, entry) -> None:
        """Populate state and UI controls from a history entry.

        Args:
            entry: A ProjectHistoryEntry with the saved configuration.
        """
        self.state.project_name = entry.project_name
        self.state.project_path = entry.project_path
        self._apply_common_config(entry)

        self.controls.project_name_input.value = entry.project_name
        self.controls.project_path_input.value = entry.project_path

        self.state.path_valid = Path(entry.project_path).is_dir()
        self._set_validation_icon(
            self.controls.project_path_input, self.state.path_valid
        )

        is_valid, _ = validate_project_name(entry.project_name)
        self.state.name_valid = is_valid
        if is_valid:
            full_path = Path(entry.project_path) / entry.project_name
            if full_path.exists():
                self.state.name_valid = False
        self._set_validation_icon(
            self.controls.project_name_input,
            self.state.name_valid if entry.project_name else None,
        )

        self._update_path_preview()
        self.controls.pypi_status_text.value = ""
        self.controls.check_pypi_button.disabled = not self.state.name_valid
        self.controls.warning_banner.value = ""
        self.page.title = (
            f"UV Forger — {entry.project_name}"
            if self.state.name_valid
            else "UV Forger"
        )
        self._show_snackbar(f"Restored: {entry.project_name}")
        self.page.update()

    def _apply_preset(self, preset) -> None:
        """Populate state and UI controls from a preset.

        Like _restore_from_history but skips project_name/path and applies metadata.

        Args:
            preset: A ProjectPreset with the saved configuration.
        """
        self._apply_common_config(preset)

        self.state.author_name = getattr(preset, "author_name", "")
        self.state.author_email = getattr(preset, "author_email", "")
        self.state.description = getattr(preset, "description", "")
        self.state.license_type = getattr(preset, "license_type", "")

        self.controls.preset_dropdown.value = preset.name
        self._update_metadata_summary()
        has_metadata = any(
            [
                self.state.author_name,
                self.state.author_email,
                self.state.description,
                self.state.license_type,
            ]
        )
        self.controls.metadata_checkbox.value = has_metadata
        self._style_selected_checkbox(self.controls.metadata_checkbox)

        self._show_snackbar(f"Preset applied: {preset.name}")
        self.page.update()

    def on_preset_quick_select(self, value: str) -> None:
        """Handle preset selection from the quick-select dropdown."""
        if not value or value == "None":
            return
        presets = load_presets()
        for preset in presets:
            if preset.name == value:
                self._apply_preset(preset)
                return

    def _refresh_preset_dropdown(self) -> None:
        """Refresh the preset dropdown options from disk."""
        self.controls.preset_dropdown.options = [p.name for p in load_presets()]

    def _save_current_as_preset(self, name: str) -> None:
        """Save the current state as a named preset.

        Args:
            name: User-given label for the preset.
        """
        preset = make_preset(
            name=name,
            python_version=self.state.python_version,
            git_enabled=self.state.git_enabled,
            include_starter_files=self.state.include_starter_files,
            ui_project_enabled=self.state.ui_project_enabled,
            framework=self.state.framework,
            other_project_enabled=self.state.other_project_enabled,
            project_type=self.state.project_type,
            folders=self.state.folders,
            packages=self.state.packages,
            dev_packages=list(self.state.dev_packages),
            imported_structure=self.state.imported_structure,
            root_files=list(self.state.root_files),
            author_name=self.state.author_name,
            author_email=self.state.author_email,
            description=self.state.description,
            license_type=self.state.license_type,
        )
        add_preset(preset)

    async def on_build_project(self, e: ft.ControlEvent) -> None:
        """Handle Build Project button click.

        Validates inputs and shows a confirmation dialog before building.
        """
        if not self._validate_inputs():
            return

        # Pre-flight check for GitHub remote mode
        if self.state.git_enabled and self.state.settings.git_remote_mode == "github":
            if not await AsyncExecutor.run(check_gh_available):
                self._show_snackbar(
                    "GitHub CLI (gh) not installed — install from https://cli.github.com",
                    is_error=True,
                )
                return
            if not await AsyncExecutor.run(check_gh_authenticated):
                self._show_snackbar(
                    "GitHub CLI not authenticated — run 'gh auth login' first",
                    is_error=True,
                )
                return

        folder_count, file_count = self._count_folders_and_files(self.state.folders)

        async def on_confirm(_):
            open_folder = dialog.open_folder_checkbox.value
            open_ide = dialog.open_ide_checkbox.value
            open_terminal = dialog.open_terminal_checkbox.value
            post_build_enabled = dialog.post_build_checkbox.value
            post_build_cmd = dialog.post_build_command_field.value
            remote_mode = getattr(dialog, "git_remote_mode_value", None)
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()
            await self._execute_build(
                open_folder=open_folder,
                open_ide=open_ide,
                open_terminal=open_terminal,
                post_build_command=post_build_cmd if post_build_enabled else "",
                git_remote_mode=remote_mode,
            )

        def on_cancel(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        build_config = BuildSummaryConfig(
            project_name=self.state.project_name,
            project_path=self.state.project_path,
            python_version=self.state.python_version,
            git_enabled=self.state.git_enabled,
            ui_project_enabled=self.state.ui_project_enabled,
            framework=self.state.framework if self.state.ui_project_enabled else None,
            other_project_enabled=self.state.other_project_enabled,
            project_type=self.state.project_type
            if self.state.other_project_enabled
            else None,
            starter_files=self.state.include_starter_files,
            folder_count=folder_count,
            file_count=file_count,
            packages=list(self.state.packages),
            dev_packages=list(self.state.dev_packages),
            folders=list(self.state.folders),
            author_name=self.state.author_name,
            author_email=self.state.author_email,
            description=self.state.description,
            license_type=self.state.license_type,
            file_override_count=len(self.state.file_overrides),
            post_build_command=self.state.settings.post_build_command,
            post_build_command_enabled=self.state.settings.post_build_command_enabled,
            git_remote_mode=self.state.settings.git_remote_mode,
            github_username=self.state.settings.github_username,
            github_repo_private=self.state.settings.github_repo_private,
        )

        dialog = create_build_summary_dialog(
            config=build_config,
            on_build_callback=wrap_async(on_confirm),
            on_cancel_callback=on_cancel,
            is_dark_mode=self.state.is_dark_mode,
            ide_name=self.state.settings.preferred_ide,
            open_folder_default=self.state.settings.open_folder_default,
            open_terminal_default=self.state.settings.open_terminal_default,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = on_cancel
        self.page.update()

    async def _do_reset(self) -> None:
        """Perform the actual reset of all UI controls and state."""
        self.state.reset()

        self.controls.project_path_input.value = self.state.project_path
        self.controls.project_name_input.value = ""
        self.controls.python_version_dropdown.value = self.state.python_version
        self.controls.preset_dropdown.value = "None"
        self.controls.create_git_checkbox.value = self.state.git_enabled
        self.controls.include_starter_files_checkbox.value = True
        self.controls.ui_project_checkbox.value = False
        self.controls.ui_project_checkbox.label = UI_PROJECT_CHECKBOX_LABEL
        self.controls.other_projects_checkbox.value = False
        self.controls.other_projects_checkbox.label = OTHER_PROJECT_CHECKBOX_LABEL
        for cb in (
            self.controls.create_git_checkbox,
            self.controls.ui_project_checkbox,
            self.controls.other_projects_checkbox,
        ):
            cb.label_style = None
        self._style_selected_checkbox(self.controls.include_starter_files_checkbox)
        self._style_selected_checkbox(self.controls.create_git_checkbox)
        self.controls.warning_banner.value = ""
        self.controls.pypi_status_text.value = ""
        self.controls.check_pypi_button.disabled = True
        self.controls.path_preview_text.value = "\u00a0"
        self.controls.progress_ring.visible = False
        self.controls.progress_bar.visible = False
        self.controls.progress_step_text.visible = False
        self.page.title = "UV Forger"

        self._set_validation_icon(self.controls.project_path_input, True)
        self._set_validation_icon(self.controls.project_name_input, None)
        self._update_build_button_state()

        self.controls.metadata_checkbox.value = False
        self.controls.metadata_checkbox.label_style = None
        self._reload_and_merge_templates()
        self._update_metadata_summary()

        self._set_status("All fields reset.", "info", update=True)
        await self.controls.project_name_input.focus()

    async def on_reset(self, e: ft.ControlEvent) -> None:
        """Handle Reset button click — shows confirmation dialog first."""

        async def do_reset(_):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()
            await self._do_reset()

        def cancel(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_confirm_dialog(
            title="Reset All Settings?",
            message="This will clear all selections, packages, and folder changes.",
            confirm_label="Reset",
            on_confirm=wrap_async(do_reset),
            on_cancel=cancel,
            is_dark_mode=self.state.is_dark_mode,
            confirm_icon=ft.Icons.REFRESH,
        )
        self.state.active_dialog = cancel
        self.page.show_dialog(dialog)

    async def on_keyboard_event(self, e: ft.KeyboardEvent) -> None:
        """Handle keyboard shortcuts.

        When on the /editor route, forwards shortcuts to the editor and
        handles Escape to close the editor view.

        Ctrl+Enter / Cmd+Enter — build project
        Ctrl+F / Cmd+F — add folder/file
        Ctrl+P / Cmd+P — add packages
        Ctrl+S / Cmd+S — save as preset
        Ctrl+R / Cmd+R — reset
        Ctrl+/ / Cmd+/ — open help
        Escape — close dialog or exit (opens confirmation)
        """
        # When the editor view is active, forward shortcuts to the editor
        if len(self.page.views) > 1:
            await self._handle_editor_keyboard(e)
            return

        if e.key == "Enter" and (e.ctrl or e.meta):
            if (
                self.state.path_valid
                and self.state.name_valid
                and not self.controls.build_project_button.disabled
            ):
                await self.on_build_project(e)
        elif e.key == "F" and (e.ctrl or e.meta):
            await self.on_add_folder(e)
        elif e.key == "P" and (e.ctrl or e.meta):
            await self.on_add_package(e)
        elif e.key == "S" and (e.ctrl or e.meta):
            if not self.controls.save_as_preset_button.disabled:
                await self.on_presets_click(e)
        elif e.key == "T" and (e.ctrl or e.meta):
            await self.on_import_tree(e)
        elif e.key == "R" and (e.ctrl or e.meta):
            await self.on_reset(e)
        elif e.key == "/" and (e.ctrl or e.meta):
            await self.on_help_click(e)
        elif e.key == "Escape":
            if self.state.active_dialog:
                self.state.active_dialog()
            else:
                await self.on_exit(e)

    async def _handle_editor_keyboard(self, e: ft.KeyboardEvent) -> None:
        """Forward keyboard shortcuts to the editor when on the /editor route."""
        editor_view = getattr(self.page, "editor_view_ref", None)
        if not editor_view:
            return
        editor = getattr(editor_view, "editor", None)
        if not editor:
            return

        # Escape: close search bar if open, otherwise close editor view
        if e.key == "Escape":
            if hasattr(editor, "_search_bar") and editor._search_bar.is_open:
                editor._close_search()
            elif self.state.active_dialog:
                self.state.active_dialog()
            return

        # F1: show help
        if e.key == "F1":
            editor._show_help()
            return

        # Cmd/Ctrl shortcuts
        if not (e.meta or e.ctrl):
            return
        key = e.key.upper()
        if key == "F" and not e.shift and not e.alt:
            await editor._open_search(with_replace=False)
        elif (key == "F" and e.alt) or (key == "H" and not e.shift):
            await editor._open_search(with_replace=True)
        elif key == "S" and not e.shift:
            await editor._do_save()
        elif key == "S" and e.shift:
            await editor._do_save_as()
        elif key == "D":
            editor._toggle_diff_pane()
        elif key == "G":
            await editor._handle_goto_line(None)
        elif key == "L" and not e.shift:
            editor._toggle_read_only()
        elif key == "L" and e.shift:
            editor._handle_language_click(None)
        elif key == "P" and e.shift:
            await editor._open_command_palette()
        elif key in ("=", "+"):
            editor._change_font_size(1)
        elif key in ("-", "_"):
            editor._change_font_size(-1)

    async def on_exit(self, e: ft.ControlEvent) -> None:
        """Handle Exit button click — shows confirmation dialog first."""

        async def do_exit(_):
            await self.page.window.close()

        def cancel(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_confirm_dialog(
            title="Exit Application?",
            message="Any unsaved configuration will be lost.",
            confirm_label="Exit",
            on_confirm=wrap_async(do_exit),
            on_cancel=cancel,
            is_dark_mode=self.state.is_dark_mode,
            confirm_icon=ft.Icons.EXIT_TO_APP,
        )
        self.state.active_dialog = cancel
        self.page.show_dialog(dialog)
