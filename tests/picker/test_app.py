from __future__ import annotations
import dataclasses
from src.picker.colors import RGB
from src.picker.app import State, Action, initial_state


# ---------------------------------------------------------------------------
# State construction
# ---------------------------------------------------------------------------

def test_state_is_frozen():
    s = initial_state(RGB(10, 20, 30), RGB(200, 210, 220), live=False)
    try:
        s.step = "fg"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("State should be frozen")


def test_initial_state_defaults():
    bg = RGB(10, 20, 30)
    fg = RGB(200, 210, 220)
    s = initial_state(bg, fg, live=False)
    assert s.bg == bg
    assert s.fg == fg
    assert s.step == "bg"
    assert s.model == "oklch"
    assert s.live is False
    assert s.pane == "sw"
    assert s.panes_mode == "focus"
    assert s.filter == ""
    assert s.sort_mode == "name"
    assert s.search_focused is False
    assert s.hex_input == ""
    assert s.hex_mode is False
    assert s.focused_channel == 0
    assert s.acc_value is None
    assert s.view_idx == 0
    assert s.swatch_idx == 0


def test_initial_state_live_flag():
    s = initial_state(RGB(0, 0, 0), RGB(255, 255, 255), live=True)
    assert s.live is True


def test_state_current_property_returns_bg_when_step_bg():
    s = initial_state(RGB(10, 20, 30), RGB(200, 210, 220), live=False)
    assert s.step == "bg"
    assert s.current == s.bg


def test_state_current_property_returns_fg_when_step_fg():
    s = initial_state(RGB(10, 20, 30), RGB(200, 210, 220), live=False)
    s2 = dataclasses.replace(s, step="fg")
    assert s2.current == s2.fg


def test_state_replace_produces_new_instance():
    s = initial_state(RGB(0, 0, 0), RGB(255, 255, 255), live=False)
    s2 = dataclasses.replace(s, step="fg")
    assert s.step == "bg"   # original unchanged
    assert s2.step == "fg"


def test_action_enum_has_three_members():
    assert Action.CONTINUE is not None
    assert Action.CONFIRM is not None
    assert Action.CANCEL is not None
