"""Declarative packages panel.

Step 3 of the incremental Flet declarative refactor (see `declarative-refactor.md`).
The panel renders the package list straight from :class:`AppState`; there is no
imperative control-list rebuild any more.

Invalidation is deliberately still explicit. State is passed as a *getter*,
not as the observable ``AppState`` itself: Flet subscribes a component to any
``Observable`` it receives as an argument (``_subscribe_observable_args``), and
that subscription is whole-object — every unrelated write (project name,
checkboxes, folders) would mark this panel dirty. A dirty component hit by an
imperative ``page.update()`` goes through ``Component.before_update()``, which
re-renders the body into fresh control ids *without* patching the client,
silently orphaning the subtree — the failure the file editor hit. A plain
callable is not observable, so the panel stays clean, and handlers re-render it
with ``controls.packages_panel.update()``, the one path that patches.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from uv_forger.ui.ui_config import UIConfig

if TYPE_CHECKING:
    from uv_forger.core.state import AppState


def _package_row(
    pkg: str, idx: int, state: AppState, on_select: Callable[[int], None]
) -> ft.Container:
    """Build one clickable package row with its dev/auto badges."""
    is_selected = state.selected_package_idx == idx
    row: list[ft.Control] = [
        ft.Text(
            pkg, size=UIConfig.TEXT_SIZE_SMALL, font_family="monospace", expand=True
        )
    ]
    if pkg in state.dev_packages:
        row.append(ft.Text("dev", size=10, color=ft.Colors.AMBER_400, italic=True))
    if pkg in state.auto_packages:
        row.append(ft.Text("auto", size=10, color=ft.Colors.GREY_500, italic=True))

    return ft.Container(
        content=ft.Row(row, spacing=4),
        bgcolor=UIConfig.SELECTED_ITEM_BGCOLOR if is_selected else None,
        border=ft.Border.all(
            UIConfig.BORDER_WIDTH_DEFAULT, UIConfig.SELECTED_ITEM_BORDER_COLOR
        )
        if is_selected
        else None,
        on_click=lambda _e: on_select(idx),
        padding=UIConfig.FOLDER_ITEM_PADDING,
        border_radius=2,
        margin=0,
    )


@ft.component
def PackagesPanel(
    get_state: Callable[[], AppState], on_select: Callable[[int], None]
) -> ft.Control:
    """Bordered container listing the current packages.

    Args:
        get_state: Returns the application state. A getter, not the state
            itself — see the module docstring.
        on_select: Called with the clicked package's index.
    """
    state = get_state()
    if state.packages:
        items: list[ft.Control] = [
            _package_row(pkg, idx, state, on_select)
            for idx, pkg in enumerate(state.packages)
        ]
    else:
        items = [
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

    return ft.Container(
        content=ft.Column(controls=items, spacing=0, scroll=ft.ScrollMode.AUTO),
        border=ft.Border.all(1, ft.Colors.GREY_700),
        border_radius=4,
        padding=10,
        height=UIConfig.SUBFOLDERS_HEIGHT,
        width=UIConfig.SPLIT_CONTAINER_WIDTH,
    )
