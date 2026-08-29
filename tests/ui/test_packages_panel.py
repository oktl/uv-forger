"""Tests for the declarative packages panel and how it is hosted."""

from flet.components.observable import Observable

from uv_forger.core.state import AppState
from uv_forger.ui.components import Controls, render_packages_panel


def _panel():
    state = AppState()
    controls = Controls()
    return state, controls, render_packages_panel(state, controls)


def test_panel_component_is_memoized():
    """Without memo, any imperative page.update() re-renders the panel into
    controls with new ids the client was never told about, and every click
    inside the panel is silently dropped."""
    _state, _controls, panel = _panel()

    assert panel.memoized is True


def test_panel_is_not_subscribed_to_app_state():
    """Flet subscribes a component to any Observable it receives as an argument,
    and the subscription is whole-object. Passing AppState directly would mark
    the panel dirty on every unrelated state write, and the next imperative
    page.update() would then re-render it without patching the client."""
    _state, _controls, panel = _panel()

    args = list(panel.args) + list(panel.kwargs.values())
    assert args, "panel is expected to take arguments"
    assert not any(isinstance(a, Observable) for a in args)


def test_panel_click_routes_through_controls_slot():
    """The panel is built before handlers exist, so clicks dispatch through
    controls.on_package_select, which attach_handlers() fills in later."""
    state, controls, panel = _panel()
    state.packages = ["flet", "httpx"]

    rows = panel.fn(*panel.args).content.controls

    seen = []
    controls.on_package_select = seen.append
    rows[1].on_click(None)

    assert seen == [1]
