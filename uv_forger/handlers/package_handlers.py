"""Handlers for package list display and management."""

import flet as ft

from uv_forger.core.constants import ALWAYS_DEV_PACKAGES
from uv_forger.ui.dialogs import create_add_packages_dialog, create_confirm_dialog
from uv_forger.ui.ui_config import UIConfig


class PackageHandlersMixin:
    """Mixin for package display, selection, add/remove/clear operations.

    Expects HandlerBase helpers available via self.
    """

    def _create_package_item(self, pkg: str, idx: int) -> ft.Container:
        """Create a clickable package item container.

        Auto-derived packages (from framework/project type maps) show a muted
        'auto' badge on the right to distinguish them from manually added ones.

        Args:
            pkg: Package name to display.
            idx: Index of the package in the list (used for selection tracking).

        Returns:
            Configured Container with click handler and selection highlighting.
        """
        is_selected = self.state.selected_package_idx == idx
        is_auto = pkg in self.state.auto_packages
        is_dev = pkg in self.state.dev_packages

        row_controls: list[ft.Control] = [
            ft.Text(
                pkg,
                size=UIConfig.TEXT_SIZE_SMALL,
                font_family="monospace",
                expand=True,
            )
        ]
        if is_dev:
            row_controls.append(
                ft.Text("dev", size=10, color=ft.Colors.AMBER_400, italic=True)
            )
        if is_auto:
            row_controls.append(
                ft.Text("auto", size=10, color=ft.Colors.GREY_500, italic=True)
            )

        return ft.Container(
            content=ft.Row(row_controls, spacing=4),
            data={"idx": idx, "name": pkg},
            bgcolor=UIConfig.SELECTED_ITEM_BGCOLOR if is_selected else None,
            border=(
                ft.Border.all(
                    UIConfig.BORDER_WIDTH_DEFAULT, UIConfig.SELECTED_ITEM_BORDER_COLOR
                )
                if is_selected
                else None
            ),
            on_click=self._on_package_click,
            padding=UIConfig.FOLDER_ITEM_PADDING,
            border_radius=2,
            margin=0,
        )

    def _update_package_display(self) -> None:
        """Update the packages container with the current package list."""
        # Catch-all: ensure always-dev packages are marked regardless of entry path
        self.state.dev_packages = self.state.dev_packages | (
            ALWAYS_DEV_PACKAGES & set(self.state.packages)
        )
        if self.state.packages:
            package_controls = [
                self._create_package_item(pkg, idx)
                for idx, pkg in enumerate(self.state.packages)
            ]
        else:
            package_controls = [
                ft.Container(
                    content=ft.Text(
                        "No packages",
                        size=UIConfig.TEXT_SIZE_SMALL,
                        color=ft.Colors.GREY_600,
                        italic=True,
                    ),
                    padding=ft.Padding(left=4, top=4, right=0, bottom=0),
                )
            ]
        self.controls.packages_container.content.controls = package_controls
        count = len(self.state.packages)
        self.controls.packages_label.value = f"Packages: {count}"
        self._update_preset_button_state()
        self.page.update()

    def _on_package_click(self, e: ft.ControlEvent) -> None:
        """Handle click on a package item to select it."""
        self.state.selected_package_idx = e.control.data["idx"]
        pkg_name = e.control.data["name"]
        self._set_status(f"Selected package: {pkg_name}", "info", update=False)
        self._update_package_display()

    async def on_add_package(self, e: ft.ControlEvent) -> None:
        """Handle Add Packages button click.

        Opens a dialog where the user can enter one or more package names
        (one per line or comma-separated). Deduplicates against the existing list.
        """
        existing = set(self.state.packages)

        def on_packages_entered(new_packages: list[str], dev: bool = False) -> None:
            added = [pkg for pkg in new_packages if pkg not in existing]
            self.state.packages.extend(added)
            existing.update(added)
            new_dev = set(added) if dev else set()
            # Auto-mark always-dev packages
            new_dev |= ALWAYS_DEV_PACKAGES & set(added)
            self.state.dev_packages = self.state.dev_packages | new_dev
            dialog.open = False
            self.state.active_dialog = None
            self._update_package_display()
            if added:
                suffix = " as dev" if dev else ""
                self._set_status(
                    f"Added {len(added)} package(s){suffix}: {', '.join(added)}",
                    "success",
                    update=True,
                )
            else:
                self._set_status(
                    "All entered packages are already in the list.",
                    "info",
                    update=True,
                )

        def on_close(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_add_packages_dialog(
            on_add_callback=on_packages_entered,
            on_close_callback=on_close,
            is_dark_mode=self.state.is_dark_mode,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.state.active_dialog = on_close
        self.page.update()

    async def on_toggle_dev(self, e: ft.ControlEvent) -> None:
        """Toggle the selected package between runtime and dev dependency."""
        if self.state.selected_package_idx is None:
            self._set_warning("Select a package to toggle.", update=True)
            return
        idx = self.state.selected_package_idx
        if 0 <= idx < len(self.state.packages):
            pkg = self.state.packages[idx]
            if pkg in ALWAYS_DEV_PACKAGES:
                self._set_status(
                    f"'{pkg}' is always a dev dependency.", "info", update=True
                )
                return
            if pkg in self.state.dev_packages:
                self.state.dev_packages = self.state.dev_packages - {pkg}
                self._set_status(f"'{pkg}' moved to runtime.", "info", update=False)
            else:
                self.state.dev_packages = self.state.dev_packages | {pkg}
                self._set_status(f"'{pkg}' moved to dev.", "info", update=False)
            self._update_package_display()

    async def on_clear_packages(self, e: ft.ControlEvent) -> None:
        """Handle Clear All packages button click.

        Shows a confirmation dialog, then removes all packages from the
        install list (both auto and manual) if confirmed.
        """
        if not self.state.packages:
            return

        count = len(self.state.packages)

        def do_clear(_):
            dialog.open = False
            self.state.active_dialog = None
            self.state.packages = []
            self.state.auto_packages = []
            self.state.dev_packages = set()
            self.state.selected_package_idx = None
            self._update_package_display()
            self._set_status("All packages cleared.", "info", update=True)

        def cancel(_=None):
            dialog.open = False
            self.state.active_dialog = None
            self.page.update()

        dialog = create_confirm_dialog(
            title="Clear All Packages?",
            message=(
                f"This will remove all {count} package(s) from the install list, "
                "including any you added manually. Framework and project type "
                "packages will be restored on the next template reload."
            ),
            confirm_label="Clear All",
            on_confirm=do_clear,
            on_cancel=cancel,
            is_dark_mode=self.state.is_dark_mode,
            confirm_icon=ft.Icons.DELETE_SWEEP,
        )
        self.state.active_dialog = cancel
        self.page.show_dialog(dialog)

    async def on_remove_package(self, e: ft.ControlEvent) -> None:
        """Handle Remove Package button click.

        Removes the currently selected package from the install list.
        """
        if self.state.selected_package_idx is None:
            self._set_warning("Select a package to remove.", update=True)
            return
        idx = self.state.selected_package_idx
        if 0 <= idx < len(self.state.packages):
            pkg = self.state.packages.pop(idx)
            self.state.dev_packages = self.state.dev_packages - {pkg}
            self.state.selected_package_idx = None
            self._update_package_display()
            self._set_status(f"Package '{pkg}' removed.", "success", update=True)
        else:
            self._set_warning("Cannot remove package: index out of range.", update=True)
