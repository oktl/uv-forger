"""Tests for AppState's observable behaviour.

AppState is decorated with ``@ft.observable`` so declarative components can
subscribe to it. These tests pin the notification contract — in particular the
asymmetry between list/dict fields (wrapped, so in-place mutation notifies) and
set fields (not wrapped, so only reassignment notifies).
"""

import json
from dataclasses import asdict

import flet as ft
import pytest

from uv_forger.core.history_manager import make_history_entry
from uv_forger.core.models import to_plain
from uv_forger.core.preset_manager import make_preset
from uv_forger.core.state import AppState


@pytest.fixture
def state_and_events():
    """An AppState with a subscribed listener recording changed field names.

    The listener is held in a list because Observable stores subscribers in a
    WeakSet — a bare lambda would be garbage collected and never fire.
    """
    state = AppState()
    events: list[str | None] = []

    def listener(_sender, field):
        events.append(field)

    state.subscribe(listener)
    return state, events, listener


class TestNotifications:
    def test_appstate_is_observable(self):
        assert isinstance(AppState(), ft.Observable)

    def test_scalar_assignment_notifies(self, state_and_events):
        state, events, _listener = state_and_events
        state.project_name = "demo"
        assert events == ["project_name"]

    def test_assigning_same_value_does_not_notify(self, state_and_events):
        state, events, _listener = state_and_events
        state.project_name = "demo"
        state.project_name = "demo"
        assert events == ["project_name"]

    def test_list_mutation_notifies_in_place(self, state_and_events):
        state, events, _listener = state_and_events
        state.packages.append("httpx")
        assert events == ["packages"]

    def test_dict_mutation_notifies_in_place(self, state_and_events):
        state, events, _listener = state_and_events
        state.file_overrides["main.py"] = "print('hi')"
        assert events == ["file_overrides"]

    def test_set_reassignment_notifies(self, state_and_events):
        state, events, _listener = state_and_events
        state.dev_packages = state.dev_packages | {"ruff"}
        assert events == ["dev_packages"]

    def test_set_in_place_mutation_does_not_notify(self, state_and_events):
        """Sets are not wrapped — handlers must rebind, never mutate in place.

        This is a guard, not an endorsement: if Flet ever starts wrapping sets
        this test fails and the rebinding in the package handlers can be
        simplified back to ``|=``.
        """
        state, events, _listener = state_and_events
        state.dev_packages.add("ruff")
        assert events == []

    def test_reset_still_produces_clean_state(self, state_and_events):
        state, _events, _listener = state_and_events
        state.project_name = "demo"
        state.packages.append("httpx")
        state.dev_packages = {"ruff"}
        state.reset()
        assert state.project_name == ""
        assert list(state.packages) == []
        assert state.dev_packages == set()

    def test_collections_stay_wrapped_after_reset(self, state_and_events):
        """reset() reassigns every field, so the fresh collections rewrap."""
        state, events, _listener = state_and_events
        state.reset()
        events.clear()
        state.packages.append("httpx")
        assert events == ["packages"]


class TestSerialization:
    """Observable collections must not leak into anything asdict() touches."""

    @staticmethod
    def _populated_state() -> AppState:
        state = AppState()
        state.folders.append(
            {"name": "core", "files": ["state.py"], "subfolders": [{"name": "sub"}]}
        )
        state.packages.append("httpx")
        return state

    def test_to_plain_unwraps_nested_observables(self):
        state = self._populated_state()
        plain = to_plain(state.folders)
        assert type(plain) is list
        assert type(plain[0]) is dict
        assert type(plain[0]["subfolders"][0]) is dict
        assert plain == [
            {"name": "core", "files": ["state.py"], "subfolders": [{"name": "sub"}]}
        ]

    def test_preset_from_live_state_serializes(self):
        state = self._populated_state()
        preset = make_preset(
            name="p",
            python_version="3.12",
            git_enabled=True,
            include_starter_files=True,
            ui_project_enabled=False,
            framework=None,
            other_project_enabled=False,
            project_type=None,
            folders=state.folders,
            packages=state.packages,
        )
        assert json.dumps([asdict(preset)])

    def test_history_entry_from_live_state_serializes(self):
        state = self._populated_state()
        entry = make_history_entry(
            project_name="n",
            project_path="/tmp/n",
            python_version="3.12",
            git_enabled=True,
            include_starter_files=True,
            ui_project_enabled=False,
            framework=None,
            other_project_enabled=False,
            project_type=None,
            folders=state.folders,
            packages=state.packages,
        )
        assert json.dumps([asdict(entry)])
