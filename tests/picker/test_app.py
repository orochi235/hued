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


from src.picker.app import update, _channel_value, _apply_channel
from src.picker.keys import Key, KeyEvent


# ---------------------------------------------------------------------------
# Channel-value helpers
# ---------------------------------------------------------------------------

def _ev(key: Key, char: str = "", shift: bool = False, ctrl: bool = False) -> KeyEvent:
    """Shortcut to build a KeyEvent for tests."""
    return KeyEvent(key=key, char=char if char else None, shift=shift, ctrl=ctrl)


def _char(c: str) -> KeyEvent:
    return KeyEvent(key=Key.CHAR, char=c, shift=False, ctrl=False)


def test_channel_value_rgb():
    from src.picker.app import _channel_value
    rgb = RGB(10, 20, 30)
    assert _channel_value("rgb", rgb, 0) == 10   # R
    assert _channel_value("rgb", rgb, 1) == 20   # G
    assert _channel_value("rgb", rgb, 2) == 30   # B


def test_channel_value_hsl():
    from src.picker.app import _channel_value
    from src.picker.colors import rgb_to_hsl
    rgb = RGB(255, 0, 0)  # pure red -> H=0, S=100, L=50
    hsl = rgb_to_hsl(rgb)
    assert _channel_value("hsl", rgb, 0) == round(hsl.h)
    assert _channel_value("hsl", rgb, 1) == round(hsl.s)
    assert _channel_value("hsl", rgb, 2) == round(hsl.l)


def test_channel_value_oklch():
    from src.picker.app import _channel_value
    from src.picker.colors import rgb_to_oklch
    rgb = RGB(100, 150, 200)
    oklch = rgb_to_oklch(rgb)
    assert _channel_value("oklch", rgb, 0) == oklch.l
    assert _channel_value("oklch", rgb, 1) == oklch.c
    assert _channel_value("oklch", rgb, 2) == oklch.h


def test_channel_value_lab():
    from src.picker.app import _channel_value
    from src.picker.colors import rgb_to_lab
    rgb = RGB(100, 150, 200)
    lab = rgb_to_lab(rgb)
    assert _channel_value("lab", rgb, 0) == lab.l
    assert _channel_value("lab", rgb, 1) == lab.a + 128   # slider uses 0-255 range
    assert _channel_value("lab", rgb, 2) == lab.b + 128


def test_apply_channel_rgb_clamps():
    from src.picker.app import _apply_channel
    base = RGB(0, 128, 255)
    # Set R to 300 -> clamped to 255
    result = _apply_channel("rgb", base, 0, 300)
    assert result.r == 255
    assert result.g == 128  # unchanged
    # Set G to -5 -> clamped to 0
    result2 = _apply_channel("rgb", base, 1, -5)
    assert result2.g == 0


def test_apply_channel_hsl_round_trips():
    from src.picker.app import _apply_channel
    from src.picker.colors import rgb_to_hsl
    base = RGB(255, 0, 0)  # H=0, S=100, L=50
    # Set S to 50
    result = _apply_channel("hsl", base, 1, 50)
    hsl_out = rgb_to_hsl(result)
    assert abs(round(hsl_out.s) - 50) <= 2


def test_apply_channel_oklch_clamps():
    from src.picker.app import _apply_channel
    base = RGB(100, 150, 200)
    # Set C to 500 -> clamped to 400
    result = _apply_channel("oklch", base, 1, 500)
    from src.picker.colors import rgb_to_oklch
    out = rgb_to_oklch(result)
    assert out.c <= 400


def test_apply_channel_lab_slider_range():
    from src.picker.app import _apply_channel
    from src.picker.colors import rgb_to_lab
    base = RGB(100, 150, 200)
    # Set lab.a slider to 128 (raw_a = 0)
    result = _apply_channel("lab", base, 1, 128)
    lab_out = rgb_to_lab(result)
    assert abs(lab_out.a) <= 5   # should be near 0

# ---------------------------------------------------------------------------
# update() skeleton — UNKNOWN key returns (unchanged_state, CONTINUE)
# ---------------------------------------------------------------------------

def _default_state() -> State:
    return initial_state(RGB(20, 40, 60), RGB(200, 180, 160), live=False)


def test_update_unknown_key_returns_continue():
    s = _default_state()
    ev = KeyEvent(key=Key.UNKNOWN, char=None, shift=False, ctrl=False)
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s == s


# ---------------------------------------------------------------------------
# Task 3: global keys + search mode
# ---------------------------------------------------------------------------

def test_ctrl_c_returns_cancel():
    s = _default_state()
    ev = KeyEvent(key=Key.CTRL_C, char=None, shift=False, ctrl=True)
    _, action = update(s, ev)
    assert action is Action.CANCEL


def test_escape_in_focus_mode_enters_nav():
    s = dataclasses.replace(_default_state(), panes_mode="focus")
    ev = KeyEvent(key=Key.ESC, char=None, shift=False, ctrl=False)
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.panes_mode == "nav"


def test_escape_in_nav_mode_is_noop():
    s = dataclasses.replace(_default_state(), panes_mode="nav")
    ev = KeyEvent(key=Key.ESC, char=None, shift=False, ctrl=False)
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.panes_mode == "nav"  # unchanged


def test_tab_cycles_pane_and_enters_nav():
    s = dataclasses.replace(_default_state(), pane="nw", panes_mode="focus",
                            focused_channel=2, acc_value=50)
    ev = KeyEvent(key=Key.TAB, char=None, shift=False, ctrl=False)
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.pane == "sw"          # nw -> sw (next in PANE_ORDER)
    assert new_s.focused_channel == 0
    assert new_s.acc_value is None
    assert new_s.panes_mode == "nav"


def test_tab_wraps_from_last_pane():
    s = dataclasses.replace(_default_state(), pane="se")
    ev = KeyEvent(key=Key.TAB, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.pane == "nw"   # se wraps to nw


def test_backtick_cycles_model_and_resets():
    s = dataclasses.replace(_default_state(), model="rgb", acc_value=100, view_idx=2)
    ev = _char("`")
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.model == "hsl"    # rgb -> hsl
    assert new_s.acc_value is None
    assert new_s.view_idx == 0


def test_backtick_wraps_last_model():
    s = dataclasses.replace(_default_state(), model="lab")
    new_s, _ = update(s, _char("`"))
    assert new_s.model == "rgb"   # lab wraps to rgb


def test_hash_enters_hex_mode():
    s = dataclasses.replace(_default_state(), panes_mode="nav", pane="nw",
                            hex_mode=False)
    ev = _char("#")
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.hex_mode is True
    assert new_s.pane == "sw"
    assert new_s.panes_mode == "focus"
    assert new_s.hex_input == "#"


def test_slash_enters_search():
    s = _default_state()
    ev = _char("/")
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.search_focused is True


def test_backslash_cycles_sort_mode():
    s = dataclasses.replace(_default_state(), sort_mode="name")
    ev = _char("\\")
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.sort_mode == "hue"


def test_backslash_wraps_sort_mode():
    s = dataclasses.replace(_default_state(), sort_mode="hue")
    new_s, _ = update(s, _char("\\"))
    assert new_s.sort_mode == "name"


def test_bracket_left_decrements_view():
    s = dataclasses.replace(_default_state(), model="rgb", view_idx=2)
    new_s, _ = update(s, _char("["))
    assert new_s.view_idx == 1


def test_bracket_left_wraps():
    from src.picker.components.slicer import VIEWS
    s = dataclasses.replace(_default_state(), model="rgb", view_idx=0)
    new_s, _ = update(s, _char("["))
    assert new_s.view_idx == len(VIEWS["rgb"]) - 1


def test_bracket_right_increments_view():
    s = dataclasses.replace(_default_state(), model="rgb", view_idx=0)
    new_s, _ = update(s, _char("]"))
    assert new_s.view_idx == 1


def test_bracket_right_wraps():
    from src.picker.components.slicer import VIEWS
    s = dataclasses.replace(_default_state(), model="rgb",
                            view_idx=len(VIEWS["rgb"]) - 1)
    new_s, _ = update(s, _char("]"))
    assert new_s.view_idx == 0


# Search-focused mode
def test_search_escape_clears_focus():
    s = dataclasses.replace(_default_state(), search_focused=True, filter="red")
    ev = KeyEvent(key=Key.ESC, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.search_focused is False
    assert new_s.filter == "red"   # filter not cleared on escape


def test_search_enter_closes_and_focuses_ne():
    s = dataclasses.replace(_default_state(), search_focused=True, pane="sw")
    ev = KeyEvent(key=Key.ENTER, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.search_focused is False
    assert new_s.pane == "ne"
    assert new_s.panes_mode == "focus"


def test_search_tab_closes_and_focuses_ne():
    s = dataclasses.replace(_default_state(), search_focused=True)
    ev = KeyEvent(key=Key.TAB, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.search_focused is False
    assert new_s.pane == "ne"
    assert new_s.panes_mode == "focus"


def test_search_alphanumeric_appends_to_filter():
    s = dataclasses.replace(_default_state(), search_focused=True, filter="re")
    ev = _char("d")
    new_s, _ = update(s, ev)
    assert new_s.filter == "red"


def test_search_non_alphanumeric_ignored():
    s = dataclasses.replace(_default_state(), search_focused=True, filter="re")
    ev = _char("!")
    new_s, _ = update(s, ev)
    assert new_s.filter == "re"   # unchanged


def test_search_backspace_trims_filter():
    s = dataclasses.replace(_default_state(), search_focused=True, filter="red")
    ev = KeyEvent(key=Key.BACKSPACE, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.filter == "re"


def test_search_delete_trims_filter():
    s = dataclasses.replace(_default_state(), search_focused=True, filter="red")
    ev = KeyEvent(key=Key.DELETE, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.filter == "re"


def test_search_other_key_is_ignored():
    # An arrow key while search_focused should not change state (and not leak to other branches)
    s = dataclasses.replace(_default_state(), search_focused=True, filter="r",
                            pane="sw", panes_mode="focus")
    ev = KeyEvent(key=Key.ARROW_UP, char=None, shift=False, ctrl=False)
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.filter == "r"       # unchanged — arrow not appended
    assert new_s.pane == "sw"        # pane not changed
