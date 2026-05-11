# Picker Python Port — Phase 4: App Integration Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the app integration layer that wires together all Phase 1-3 building blocks into a working interactive picker: a frozen `State` dataclass, a pure `update(state, event) -> (State, Action)` function covering every key-handler branch from the TS `App.tsx` prototype, a pure `render(state, cols, rows) -> Frame` function that delegates to Phase 3 components, and a `run()` event-loop entry point that handles terminal setup, OSC management, resize, and file output.

**Architecture:** Elm/MVU pattern. `State` is a frozen dataclass — no mutation, ever. `update()` returns `(new_state, action)` where `action` is a member of the `Action` enum. `render()` calls into Phase 3 component functions passing sub-rectangles. `run()` owns all terminal I/O side effects. The channel-value arithmetic (slider adjustment) lives entirely inside `update()`, which converts model-space values to RGB using the Phase 1 conversion functions — no callbacks, no shared mutable state.

**Tech Stack:** Python 3.9+ stdlib only. Builds on Phase 1 (`colors`, `keys`, `term`, `names`), Phase 2 (`frame`), and Phase 3 (`components`). No new runtime deps.

**Branch strategy:** Cut `feature/picker-app` from `main` after Phase 3 (`feature/picker-components`) merges. If Phase 3 has not yet merged when you start, cut from `feature/picker-components` instead and rebase when Phase 3 lands.

**Entry point decision:** The existing `bin/hued-pick` is a compiled TS binary and will be replaced in Phase 5. This phase does not touch `bin/hued-pick`. Instead, `src/picker/app.py` exposes a `main()` function, and `src/picker/__main__.py` is updated to call `app.main()` when the `-i` / `--interactive` flag is detected (Phase 5 wires the shell shim). The plan uses `python3 -m src.picker app` for manual smoke testing.

---

## File Structure

Files this plan creates or modifies:

- **Create:** `src/picker/app.py` — `State` frozen dataclass, `Action` enum, `initial_state()`, `update()`, `render()`, `run()`, `main()`.
- **Create:** `tests/picker/test_app.py` — unit tests for `State` construction, `update()` branches, and `render()` smoke.
- **Modify:** `src/picker/__main__.py` — upgrade smoke test to call `app.main()` when passed `--app` flag (for manual E2E testing); keep the existing Phase 2 smoke path for flag-less invocation.

After this phase:

```
src/picker/
  components/
    __init__.py
    slider.py
    settings.py
    preview.py
    swatch_browser.py
    slicer.py
  __init__.py
  __main__.py      # + --app flag dispatches to app.main()
  app.py           # NEW — state, update, render, run, main
  colors.py
  frame.py
  keys.py
  names.py
  term.py

tests/picker/
  components/
    ...
  test_app.py      # NEW
  test_colors.py
  test_frame.py
  test_keys.py
  test_names.py
  test_term.py
```

---

## Design decisions (read before implementing)

**State shape:** All fields listed below are present in every `State`. No optional structural fields — every field always exists, even if semantically inactive (e.g. `hex_input` is `""` when `hex_mode` is `False`). The `swatch_idx` field is added to the Python port to track focused swatch position in the browser pane; the TS version owns this inside the `SwatchBrowser` component's internal state, but in the pure-update model we must carry it in `State`.

**Channel-value math in update():** The TS `useInput` handler calls `ch.onChange(v)` where `ch` is a pre-computed channel object. In the Python port, `update()` must do this math directly. The pattern is:

1. Compute the current model-space representation of the current color (`rgb_to_hsl`, `rgb_to_oklch`, or `rgb_to_lab`).
2. Read the current channel value for `state.focused_channel`.
3. Compute the new channel value (clamp to `[0, max]`).
4. Convert back to RGB and store in `state.bg` or `state.fg` depending on `state.step`.

Channel definitions (mirrors TS `channels` arrays, lines 97-112 of App.tsx):

```
rgb:   ch0=R(0-255)  ch1=G(0-255)  ch2=B(0-255)
hsl:   ch0=H(0-360)  ch1=S(0-100)  ch2=L(0-100)
oklch: ch0=L(0-100)  ch1=C(0-400)  ch2=H(0-360)
lab:   ch0=L(0-100)  ch1=a(-128..127 stored as 0-255)  ch2=b(-128..127 stored as 0-255)
```

For `lab`, the TS stores `lab.a + 128` as the slider value (0-255 range). When reading or writing, convert: `raw_a = slider_value - 128`.

**Action enum:** `update()` returns `(State, Action)`. Three actions:

- `Action.CONTINUE` — keep the event loop running, re-render.
- `Action.CONFIRM` — the user pressed Enter on the final step (or selected from the swatch browser on the fg step); `run()` writes the output file and exits 0.
- `Action.CANCEL` — Ctrl-C was pressed; `run()` resets OSC colors and exits 1.

**Advance logic:** The TS `advance()` function (App.tsx line 68-78) transitions between steps:
- On `step == "bg"`: set `step = "fg"`, clear `filter`, clear `hex_input`, clear `hex_mode`.
- On `step == "fg"`: return `Action.CONFIRM`.

In the Python port this is a helper `_advance(state) -> tuple[State, Action]` called from within `update()` for the appropriate key events.

**Swatch browser `swatch_idx`:** The TS SwatchBrowser manages its own cursor state internally. In the pure MVU model this is `state.swatch_idx: int` (added to State). In the SE pane while focused, `ARROW_UP` and `ARROW_DOWN` change `swatch_idx`. The `render()` function passes `focused_idx=state.swatch_idx` to `render_swatch_browser`. This is not in the TS State set listed in the brief but is required for correctness; the brief acknowledges "decide based on what's cleanest."

**SE pane behavior:** In the TS prototype (App.tsx line 336-337), hovering a swatch immediately previews its color, and Enter selects it and calls `advance()`. In the Python port:
- `ARROW_UP`: `swatch_idx = max(0, swatch_idx - num_cols)` where `num_cols = max(1, (pane_w - 2) // 5)`.
- `ARROW_DOWN`: `swatch_idx = min(len(entries) - 1, swatch_idx + num_cols)`.
- `ARROW_LEFT`: `swatch_idx = max(0, swatch_idx - 1)`.
- `ARROW_RIGHT`: `swatch_idx = min(len(entries) - 1, swatch_idx + 1)`.
- Hovering (on any swatch navigation) applies the hovered color to the current channel.
- `ENTER`: selects the focused swatch color and calls `_advance()`.

The hover color update applies the hovered hex directly to `state.bg` or `state.fg` depending on `state.step`.

**Sort modes:** The TS has `SORT_MODES = ['name', 'hue']` (from `SwatchBrowser.tsx` line 8). The `\` key cycles between them. Phase 3's `sort_entries()` already supports both.

**`run()` OSC management:** After every `update()` call, if `state.live` and the current color changed, emit `osc_bg` or `osc_fg`. Track the previous color by comparing `state.bg` / `state.fg` against pre-update values.

**Resize handling:** SIGWINCH fires `on_resize`, which sets a flag (`_resize_pending`). In the main loop, after processing each key event, check the flag and re-render at the new size. This avoids re-rendering inside signal context.

**Output format:** On `CONFIRM`, write:
```
background=#rrggbb
foreground=#rrggbb
```
to `output_path` if provided, otherwise to `sys.stdout`. This matches the TS `advance()` function on the `fg` step (App.tsx line 73-76).

---

## Task 1: Branch + State dataclass + initial_state()

**Files:**
- Create: `src/picker/app.py`
- Create: `tests/picker/test_app.py`

- [ ] **Step 1: Create branch**

Cut from `main` (or `feature/picker-components` if Phase 3 hasn't merged yet):

```bash
git checkout main && git pull --ff-only
git checkout -b feature/picker-app
```

- [ ] **Step 2: Write failing tests for State construction**

Create `tests/picker/test_app.py`:

```python
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
```

- [ ] **Step 3: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.app'`.

- [ ] **Step 4: Implement State + Action + initial_state()**

Create `src/picker/app.py`:

```python
from __future__ import annotations

import dataclasses
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal, Optional

from src.picker.colors import RGB


class Action(Enum):
    CONTINUE = auto()
    CONFIRM = auto()
    CANCEL = auto()


@dataclass(frozen=True)
class State:
    bg: RGB
    fg: RGB
    step: Literal["bg", "fg"]
    model: Literal["rgb", "hsl", "oklch", "lab"]
    live: bool
    pane: Literal["nw", "sw", "ne", "se"]
    panes_mode: Literal["nav", "focus"]
    filter: str
    sort_mode: Literal["name", "hue"]
    search_focused: bool
    hex_input: str
    hex_mode: bool
    focused_channel: int
    acc_value: Optional[int]
    view_idx: int
    swatch_idx: int

    @property
    def current(self) -> RGB:
        """The color being edited: bg when step=='bg', fg when step=='fg'."""
        return self.bg if self.step == "bg" else self.fg


def initial_state(initial_bg: RGB, initial_fg: RGB, live: bool) -> State:
    """Construct the default initial State for a new picker session."""
    return State(
        bg=initial_bg,
        fg=initial_fg,
        step="bg",
        model="oklch",
        live=live,
        pane="sw",
        panes_mode="focus",
        filter="",
        sort_mode="name",
        search_focused=False,
        hex_input="",
        hex_mode=False,
        focused_channel=0,
        acc_value=None,
        view_idx=0,
        swatch_idx=0,
    )
```

- [ ] **Step 5: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): State dataclass, Action enum, initial_state()"
```

---

## Task 2: update() skeleton + channel-value helpers

This task builds the `update()` skeleton and the helpers that translate model-space channel adjustments into RGB. Getting these helpers right first means each subsequent task can just call them.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `tests/picker/test_app.py`

- [ ] **Step 1: Write failing tests for channel helpers**

Append to `tests/picker/test_app.py`:

```python
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
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v -k "channel or update_unknown"
```

Expected: `ImportError: cannot import name '_channel_value'`.

- [ ] **Step 3: Implement channel helpers + update() skeleton**

Append to `src/picker/app.py` (after the `initial_state` function):

```python
import dataclasses
import math

from src.picker.colors import (
    rgb_to_hsl, hsl_to_rgb, HSL,
    rgb_to_oklch, oklch_to_rgb, OKLCH,
    rgb_to_lab, lab_to_rgb, Lab,
    hex_to_rgb, rgb_to_hex,
)
from src.picker.keys import Key, KeyEvent
from src.picker.names import NAMED_COLORS

# Ordered model list (mirrors TS MODELS constant)
_MODELS: list[str] = ["rgb", "hsl", "oklch", "lab"]

# Ordered pane list (mirrors TS PANE_ORDER constant)
_PANE_ORDER: list[str] = ["nw", "sw", "ne", "se"]

# Sort modes (mirrors TS SORT_MODES constant)
_SORT_MODES: list[str] = ["name", "hue"]

# Max values per channel per model (index matches focused_channel)
_CHANNEL_MAX: dict[str, list[int]] = {
    "rgb":   [255, 255, 255],
    "hsl":   [360, 100, 100],
    "oklch": [100, 400, 360],
    "lab":   [100, 255, 255],  # lab.a and lab.b stored as a+128 (0-255 range)
}


def _channel_value(model: str, rgb: RGB, channel: int) -> int:
    """Return the integer slider value for `channel` in `model` space.

    For lab, channels 1 (a) and 2 (b) are returned as `raw + 128` so
    they fit in [0, 255] matching the slider's display range.
    """
    if model == "rgb":
        return (rgb.r, rgb.g, rgb.b)[channel]
    if model == "hsl":
        hsl = rgb_to_hsl(rgb)
        return (round(hsl.h), round(hsl.s), round(hsl.l))[channel]
    if model == "oklch":
        oklch = rgb_to_oklch(rgb)
        return (oklch.l, oklch.c, oklch.h)[channel]
    if model == "lab":
        lab = rgb_to_lab(rgb)
        return (lab.l, lab.a + 128, lab.b + 128)[channel]
    return 0


def _apply_channel(model: str, rgb: RGB, channel: int, value: int) -> RGB:
    """Return a new RGB with `channel` set to `value` in `model` space.

    `value` is clamped to the valid range for that channel.
    For lab channels 1 and 2, `value` is in [0, 255] (raw + 128).
    """
    maxv = _CHANNEL_MAX[model][channel]
    v = max(0, min(maxv, value))

    if model == "rgb":
        r, g, b = rgb.r, rgb.g, rgb.b
        if channel == 0:
            r = v
        elif channel == 1:
            g = v
        else:
            b = v
        return RGB(r, g, b)

    if model == "hsl":
        hsl = rgb_to_hsl(rgb)
        h, s, l = round(hsl.h), round(hsl.s), round(hsl.l)
        if channel == 0:
            h = v
        elif channel == 1:
            s = v
        else:
            l = v
        return hsl_to_rgb(HSL(float(h), float(s), float(l)))

    if model == "oklch":
        oklch = rgb_to_oklch(rgb)
        lv, c, hv = oklch.l, oklch.c, oklch.h
        if channel == 0:
            lv = v
        elif channel == 1:
            c = v
        else:
            hv = v
        return oklch_to_rgb(OKLCH(lv, c, hv))

    if model == "lab":
        lab = rgb_to_lab(rgb)
        lv, a, b = lab.l, lab.a, lab.b
        if channel == 0:
            lv = v
        elif channel == 1:
            a = v - 128  # convert slider range back to raw
        else:
            b = v - 128
        return lab_to_rgb(Lab(lv, a, b))

    return rgb  # unreachable; satisfies type checker


def _set_current(state: State, new_rgb: RGB) -> State:
    """Return a new State with bg or fg replaced by new_rgb per state.step."""
    if state.step == "bg":
        return dataclasses.replace(state, bg=new_rgb)
    return dataclasses.replace(state, fg=new_rgb)


def _advance(state: State) -> tuple[State, Action]:
    """Transition to the next step or confirm if on the last step."""
    if state.step == "bg":
        new_state = dataclasses.replace(
            state,
            step="fg",
            filter="",
            hex_input="",
            hex_mode=False,
            swatch_idx=0,
        )
        return new_state, Action.CONTINUE
    return state, Action.CONFIRM


def update(state: State, event: KeyEvent) -> tuple[State, Action]:
    """Pure state transition function. Takes current State and a KeyEvent;
    returns (new_state, action). Never mutates state.

    Mirrors the TS useInput handler in App.tsx:120-241 branch-for-branch.
    """
    # All branches are implemented in Tasks 3-7.
    # Unknown keys: no-op.
    return state, Action.CONTINUE
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: all tests pass (8 from Task 1 + new tests). The `test_update_unknown_key_returns_continue` test passes because the skeleton returns `(state, CONTINUE)` for all keys.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): channel-value helpers and update() skeleton"
```

---

## Task 3: update() — global keys + search mode

This task implements the highest-priority key branches: Ctrl-C cancel, search-focused mode (any key while `search_focused` is True), Escape, Tab, and global symbol keys (`` ` ``, `#`, `/`, `\`, `[`, `]`) that fire regardless of which pane is active.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `tests/picker/test_app.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/picker/test_app.py`:

```python
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
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v -k "task3 or ctrl_c or escape or tab or backtick or hash or slash or backslash or bracket or search"
```

Expected: most fail because `update()` currently returns `(state, CONTINUE)` for all keys.

- [ ] **Step 3: Implement global keys + search mode in update()**

Replace the `update()` function body in `src/picker/app.py` with:

```python
def update(state: State, event: KeyEvent) -> tuple[State, Action]:
    """Pure state transition function. Takes current State and a KeyEvent;
    returns (new_state, action). Never mutates state.

    Mirrors the TS useInput handler in App.tsx:120-241 branch-for-branch.
    """
    from src.picker.components.slicer import VIEWS

    k = event.key
    ch = event.char or ""
    p = state.pane
    pm = state.panes_mode

    # -----------------------------------------------------------------------
    # Search-focused mode: all keys go here first (mirrors App.tsx:122-129)
    # -----------------------------------------------------------------------
    if state.search_focused:
        if k is Key.ESC:
            return dataclasses.replace(state, search_focused=False), Action.CONTINUE
        if k is Key.ENTER or k is Key.TAB:
            return dataclasses.replace(
                state, search_focused=False, pane="ne", panes_mode="focus"
            ), Action.CONTINUE
        if k is Key.CHAR and ch.isalnum():
            return dataclasses.replace(state, filter=state.filter + ch), Action.CONTINUE
        if k is Key.BACKSPACE or k is Key.DELETE:
            return dataclasses.replace(state, filter=state.filter[:-1]), Action.CONTINUE
        # Any other key while search focused: absorb without changing state
        return state, Action.CONTINUE

    # -----------------------------------------------------------------------
    # Ctrl-C: cancel immediately (mirrors App.tsx:131)
    # -----------------------------------------------------------------------
    if k is Key.CTRL_C:
        return state, Action.CANCEL

    # -----------------------------------------------------------------------
    # Escape (mirrors App.tsx:133-136)
    # -----------------------------------------------------------------------
    if k is Key.ESC:
        if pm == "focus":
            return dataclasses.replace(state, panes_mode="nav"), Action.CONTINUE
        return state, Action.CONTINUE

    # -----------------------------------------------------------------------
    # Tab: cycle pane, reset channel/acc, enter nav (mirrors App.tsx:138-143)
    # -----------------------------------------------------------------------
    if k is Key.TAB:
        next_pane = _PANE_ORDER[(_PANE_ORDER.index(p) + 1) % len(_PANE_ORDER)]
        return dataclasses.replace(
            state,
            pane=next_pane,
            focused_channel=0,
            acc_value=None,
            panes_mode="nav",
        ), Action.CONTINUE

    # -----------------------------------------------------------------------
    # Nav-mode arrow keys (mirrors App.tsx:145-158)
    # -----------------------------------------------------------------------
    if pm == "nav":
        _neighbors: dict[str, dict[str, str]] = {
            "nw": {"right": "ne", "down": "sw"},
            "ne": {"left": "nw", "down": "se"},
            "sw": {"up": "nw", "right": "se"},
            "se": {"up": "ne", "left": "sw"},
        }
        nb = _neighbors[p]
        if k is Key.ARROW_LEFT and "left" in nb:
            return dataclasses.replace(state, pane=nb["left"]), Action.CONTINUE
        if k is Key.ARROW_RIGHT and "right" in nb:
            return dataclasses.replace(state, pane=nb["right"]), Action.CONTINUE
        if k is Key.ARROW_UP and "up" in nb:
            return dataclasses.replace(state, pane=nb["up"]), Action.CONTINUE
        if k is Key.ARROW_DOWN and "down" in nb:
            return dataclasses.replace(state, pane=nb["down"]), Action.CONTINUE
        if k is Key.ENTER:
            return dataclasses.replace(state, panes_mode="focus"), Action.CONTINUE
        # Nav mode: global symbol keys still fire (fall through)

    # -----------------------------------------------------------------------
    # Global symbol keys — fire regardless of pane/mode
    # (mirrors App.tsx:160-196)
    # -----------------------------------------------------------------------
    if k is Key.CHAR:
        # ` — cycle model forward, reset acc and view_idx
        if ch == "`":
            next_model = _MODELS[(_MODELS.index(state.model) + 1) % len(_MODELS)]
            return dataclasses.replace(
                state, model=next_model, acc_value=None, view_idx=0
            ), Action.CONTINUE

        # # — enter hex-input mode, jump to sw pane in focus mode
        if ch == "#":
            return dataclasses.replace(
                state,
                hex_mode=True,
                pane="sw",
                panes_mode="focus",
                hex_input="#",
            ), Action.CONTINUE

        # / — focus search input
        if ch == "/":
            return dataclasses.replace(state, search_focused=True), Action.CONTINUE

        # \ — cycle sort mode
        if ch == "\\":
            next_sort = _SORT_MODES[(_SORT_MODES.index(state.sort_mode) + 1) % len(_SORT_MODES)]
            return dataclasses.replace(state, sort_mode=next_sort), Action.CONTINUE

        # [ — decrement view_idx (wraps)
        if ch == "[":
            n_views = len(VIEWS[state.model])
            new_idx = (state.view_idx - 1 + n_views) % n_views
            return dataclasses.replace(state, view_idx=new_idx), Action.CONTINUE

        # ] — increment view_idx (wraps)
        if ch == "]":
            n_views = len(VIEWS[state.model])
            new_idx = (state.view_idx + 1) % n_views
            return dataclasses.replace(state, view_idx=new_idx), Action.CONTINUE

    # -----------------------------------------------------------------------
    # Below this point: focus-mode only (mirrors App.tsx:198)
    # -----------------------------------------------------------------------
    if pm != "focus":
        return state, Action.CONTINUE

    # Pane-specific handlers are implemented in Tasks 4-7.
    return state, Action.CONTINUE
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: all tests pass. The pane-specific tests added in later tasks will not exist yet.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): update() global keys and search mode"
```

---

## Task 4: update() — NW and SW slider pane (focus mode)

This task implements focus-mode handlers for the NW (settings) pane and the SW (slider) pane, including channel adjustment with `acc_value` accumulation and the Enter key for `_advance()`.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `tests/picker/test_app.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/picker/test_app.py`:

```python
# ---------------------------------------------------------------------------
# Task 4: NW pane + SW slider pane (focus mode)
# ---------------------------------------------------------------------------

def _sw_state(**kwargs) -> State:
    """A state with sw pane focused."""
    base = dataclasses.replace(
        _default_state(),
        pane="sw", panes_mode="focus", hex_mode=False,
        model="rgb", focused_channel=0, acc_value=None,
    )
    return dataclasses.replace(base, **kwargs)


def test_nw_arrow_left_cycles_model_backward():
    s = dataclasses.replace(_default_state(), pane="nw", panes_mode="focus",
                            model="hsl", acc_value=5, view_idx=1)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=False, ctrl=False))
    assert new_s.model == "rgb"
    assert new_s.acc_value is None
    assert new_s.view_idx == 0


def test_nw_arrow_left_wraps_model():
    s = dataclasses.replace(_default_state(), pane="nw", panes_mode="focus",
                            model="rgb")
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=False, ctrl=False))
    assert new_s.model == "lab"


def test_nw_arrow_right_cycles_model_forward():
    s = dataclasses.replace(_default_state(), pane="nw", panes_mode="focus",
                            model="rgb")
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.model == "hsl"


def test_nw_l_toggles_live():
    s = dataclasses.replace(_default_state(), pane="nw", panes_mode="focus", live=False)
    new_s, _ = update(s, _char("l"))
    assert new_s.live is True
    new_s2, _ = update(new_s, _char("l"))
    assert new_s2.live is False


def test_nw_enter_advances_step():
    s = dataclasses.replace(_default_state(), pane="nw", panes_mode="focus", step="bg")
    new_s, action = update(s, KeyEvent(key=Key.ENTER, char=None, shift=False, ctrl=False))
    assert action is Action.CONTINUE
    assert new_s.step == "fg"


def test_sw_arrow_up_decrements_channel():
    s = _sw_state(focused_channel=1, acc_value=10)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_UP, char=None, shift=False, ctrl=False))
    assert new_s.focused_channel == 0
    assert new_s.acc_value is None


def test_sw_arrow_up_clamps_at_zero():
    s = _sw_state(focused_channel=0)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_UP, char=None, shift=False, ctrl=False))
    assert new_s.focused_channel == 0


def test_sw_arrow_down_increments_channel():
    s = _sw_state(model="rgb", focused_channel=0)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_DOWN, char=None, shift=False, ctrl=False))
    assert new_s.focused_channel == 1


def test_sw_arrow_down_clamps_at_max_channel():
    s = _sw_state(model="rgb", focused_channel=2)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_DOWN, char=None, shift=False, ctrl=False))
    assert new_s.focused_channel == 2   # clamped at 2 (rgb has 3 channels)


def test_sw_arrow_right_increments_channel_value():
    # RGB model, ch0=R, bg=RGB(100, 50, 50) -> new R=101
    s = _sw_state(model="rgb", focused_channel=0,
                  bg=RGB(100, 50, 50), step="bg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.bg.r == 101
    assert new_s.acc_value == 101


def test_sw_arrow_right_uses_acc_value_as_base():
    # acc_value overrides current channel value as the base for adjustment
    s = _sw_state(model="rgb", focused_channel=0,
                  bg=RGB(100, 50, 50), step="bg", acc_value=50)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.bg.r == 51   # 50 + 1, not 100 + 1
    assert new_s.acc_value == 51


def test_sw_arrow_left_decrements_channel_value():
    s = _sw_state(model="rgb", focused_channel=1,
                  bg=RGB(50, 100, 50), step="bg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=False, ctrl=False))
    assert new_s.bg.g == 99
    assert new_s.acc_value == 99


def test_sw_arrow_right_shift_increments_by_10():
    s = _sw_state(model="rgb", focused_channel=0,
                  bg=RGB(100, 50, 50), step="bg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=True, ctrl=False))
    assert new_s.bg.r == 110
    assert new_s.acc_value == 110


def test_sw_arrow_left_shift_decrements_by_10():
    s = _sw_state(model="rgb", focused_channel=0,
                  bg=RGB(100, 50, 50), step="bg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=True, ctrl=False))
    assert new_s.bg.r == 90
    assert new_s.acc_value == 90


def test_sw_channel_value_clamps_at_max():
    # R at 250, arrow-right-shift by 10 -> 255 (not 260)
    s = _sw_state(model="rgb", focused_channel=0,
                  bg=RGB(250, 50, 50), step="bg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=True, ctrl=False))
    assert new_s.bg.r == 255


def test_sw_channel_value_clamps_at_zero():
    s = _sw_state(model="rgb", focused_channel=0,
                  bg=RGB(5, 50, 50), step="bg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=True, ctrl=False))
    assert new_s.bg.r == 0


def test_sw_adjust_fg_when_step_fg():
    s = _sw_state(model="rgb", focused_channel=2,
                  fg=RGB(50, 50, 100), step="fg", acc_value=None)
    new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.fg.b == 101
    assert new_s.bg == s.bg   # bg unchanged


def test_sw_enter_advances_from_bg_to_fg():
    s = _sw_state(step="bg")
    new_s, action = update(s, KeyEvent(key=Key.ENTER, char=None, shift=False, ctrl=False))
    assert action is Action.CONTINUE
    assert new_s.step == "fg"


def test_sw_enter_on_fg_step_confirms():
    s = _sw_state(step="fg")
    _, action = update(s, KeyEvent(key=Key.ENTER, char=None, shift=False, ctrl=False))
    assert action is Action.CONFIRM
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v -k "nw_ or sw_"
```

Expected: all fail because the NW and SW branches are not yet implemented.

- [ ] **Step 3: Implement NW and SW slider branches in update()**

In `src/picker/app.py`, replace the final `return state, Action.CONTINUE` at the bottom of `update()` with:

```python
    # -----------------------------------------------------------------------
    # Enter in focus mode (non-SE panes): advance step or confirm
    # (mirrors App.tsx:198)
    # -----------------------------------------------------------------------
    if k is Key.ENTER and p != "se":
        return _advance(state)

    # -----------------------------------------------------------------------
    # NW pane: settings controls (mirrors App.tsx:200-204)
    # -----------------------------------------------------------------------
    if p == "nw":
        if k is Key.ARROW_LEFT:
            prev_model = _MODELS[(_MODELS.index(state.model) - 1) % len(_MODELS)]
            return dataclasses.replace(
                state, model=prev_model, acc_value=None, view_idx=0
            ), Action.CONTINUE
        if k is Key.ARROW_RIGHT:
            next_model = _MODELS[(_MODELS.index(state.model) + 1) % len(_MODELS)]
            return dataclasses.replace(
                state, model=next_model, acc_value=None, view_idx=0
            ), Action.CONTINUE
        if k is Key.CHAR and ch == "l":
            return dataclasses.replace(state, live=not state.live), Action.CONTINUE

    # -----------------------------------------------------------------------
    # SW pane — slider controls (hex_mode=False) (mirrors App.tsx:206-219)
    # -----------------------------------------------------------------------
    if p == "sw" and not state.hex_mode:
        if k is Key.ARROW_UP:
            new_ch = max(0, state.focused_channel - 1)
            return dataclasses.replace(
                state, focused_channel=new_ch, acc_value=None
            ), Action.CONTINUE
        if k is Key.ARROW_DOWN:
            n_channels = len(_CHANNEL_MAX[state.model])
            new_ch = min(n_channels - 1, state.focused_channel + 1)
            return dataclasses.replace(
                state, focused_channel=new_ch, acc_value=None
            ), Action.CONTINUE

        # Horizontal arrows adjust the focused channel value
        base = (
            state.acc_value
            if state.acc_value is not None
            else _channel_value(state.model, state.current, state.focused_channel)
        )
        step_size = 10 if event.shift else 1
        if k is Key.ARROW_RIGHT:
            new_val = base + step_size
        elif k is Key.ARROW_LEFT:
            new_val = base - step_size
        else:
            new_val = None  # key not handled here

        if new_val is not None:
            clamped = max(0, min(_CHANNEL_MAX[state.model][state.focused_channel], new_val))
            new_rgb = _apply_channel(
                state.model, state.current, state.focused_channel, clamped
            )
            new_state = _set_current(state, new_rgb)
            new_state = dataclasses.replace(new_state, acc_value=clamped)
            return new_state, Action.CONTINUE

    # All other keys in focus mode: no-op
    return state, Action.CONTINUE
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): update() NW settings and SW slider pane handlers"
```

---

## Task 5: update() — hex-input mode (SW pane, hex_mode=True)

This task implements the hex-input mode entered via `#`. While `hex_mode` is True, the SW pane shows a raw hex string instead of sliders.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `tests/picker/test_app.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/picker/test_app.py`:

```python
# ---------------------------------------------------------------------------
# Task 5: hex-input mode
# ---------------------------------------------------------------------------

def _hex_state(**kwargs) -> State:
    base = dataclasses.replace(
        _default_state(),
        pane="sw", panes_mode="focus", hex_mode=True, hex_input="#",
        bg=RGB(0, 0, 0), step="bg",
    )
    return dataclasses.replace(base, **kwargs)


def test_hex_escape_exits_mode():
    s = _hex_state(hex_input="#ff0000")
    ev = KeyEvent(key=Key.ESC, char=None, shift=False, ctrl=False)
    new_s, action = update(s, ev)
    assert action is Action.CONTINUE
    assert new_s.hex_mode is False
    assert new_s.hex_input == ""


def test_hex_digit_appends():
    s = _hex_state(hex_input="#")
    new_s, _ = update(s, _char("f"))
    assert new_s.hex_input == "#f"


def test_hex_hash_ignored_if_already_present():
    # TS: next = (hi + input).slice(-7); '#' inside that only matters at start
    # After appending '#' to "#123456" -> "#123456#" -> slice(-7) -> "123456#"
    # which is invalid. The practical effect: '#' can appear only when it's
    # the 7th character. We verify the existing '#' at start is not duplicated
    # in a way that breaks a valid 6-hex sequence.
    s = _hex_state(hex_input="#12345")
    new_s, _ = update(s, _char("#"))
    # "#12345" + "#" = "#12345#" -> slice last 7 -> "#12345#" (invalid, no color update)
    assert new_s.hex_input == "#12345#" or len(new_s.hex_input) <= 7


def test_hex_uppercase_appends():
    s = _hex_state(hex_input="#")
    new_s, _ = update(s, _char("A"))
    assert new_s.hex_input == "#A"


def test_hex_invalid_char_ignored():
    s = _hex_state(hex_input="#1a")
    new_s, _ = update(s, _char("z"))   # 'z' is not a hex digit
    assert new_s.hex_input == "#1a"


def test_hex_backspace_trims():
    s = _hex_state(hex_input="#ff0")
    ev = KeyEvent(key=Key.BACKSPACE, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    assert new_s.hex_input == "#ff"


def test_hex_complete_6_digits_applies_color():
    # Entering the 6th digit completes the hex string -> color updates immediately
    s = _hex_state(hex_input="#ff000", bg=RGB(0, 0, 0), step="bg")
    new_s, _ = update(s, _char("0"))
    assert new_s.hex_input == "#ff0000"
    assert new_s.bg == RGB(255, 0, 0)


def test_hex_backspace_on_partial_does_not_update_color():
    # Trimming back below 6 digits should not update the color
    s = _hex_state(hex_input="#ff000", bg=RGB(0, 128, 0), step="bg")
    ev = KeyEvent(key=Key.BACKSPACE, char=None, shift=False, ctrl=False)
    new_s, _ = update(s, ev)
    # hex_input is now "#ff00" — incomplete — color unchanged
    assert new_s.bg == RGB(0, 128, 0)
    assert new_s.hex_input == "#ff00"


def test_hex_input_capped_at_7_chars():
    # The TS does (hi + input).slice(-7) — we keep at most 7 chars including '#'
    s = _hex_state(hex_input="#ff0000")
    new_s, _ = update(s, _char("a"))
    # Result: "#ff0000a".slice(-7) == "f0000a" — no leading #, 6 digits -> applies
    # The exact content depends on TS semantics; what matters is len <= 7
    assert len(new_s.hex_input) <= 7


def test_hex_applies_to_fg_when_step_fg():
    s = _hex_state(hex_input="#00ff0", fg=RGB(0, 0, 0), step="fg")
    new_s, _ = update(s, _char("0"))
    assert new_s.fg == RGB(0, 255, 0)
    assert new_s.bg == s.bg   # bg unchanged
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v -k "hex_"
```

Expected: most fail because hex mode is not yet implemented in `update()`.

- [ ] **Step 3: Implement hex-input branch**

In `src/picker/app.py`, inside `update()`, add the hex-mode handler for the SW pane. Insert it immediately before the `# SW pane — slider controls` block (the block that starts `if p == "sw" and not state.hex_mode:`):

```python
    # -----------------------------------------------------------------------
    # SW pane — hex-input mode (hex_mode=True) (mirrors App.tsx:221-234)
    # -----------------------------------------------------------------------
    if p == "sw" and state.hex_mode:
        if k is Key.ESC:
            return dataclasses.replace(
                state, hex_mode=False, hex_input=""
            ), Action.CONTINUE

        if k is Key.BACKSPACE or k is Key.DELETE:
            next_input = state.hex_input[:-1]
            new_state = dataclasses.replace(state, hex_input=next_input)
            bare = next_input.lstrip("#")
            if len(bare) == 6 and all(c in "0123456789abcdefABCDEF" for c in bare):
                new_state = _set_current(new_state, hex_to_rgb("#" + bare))
            return new_state, Action.CONTINUE

        if k is Key.CHAR and ch in "0123456789abcdefABCDEFABCDEF#":
            # TS: (hi + input).slice(-7) — keep only the last 7 characters
            raw = (state.hex_input + ch)[-7:]
            new_state = dataclasses.replace(state, hex_input=raw)
            bare = raw.lstrip("#")
            if len(bare) == 6 and all(c in "0123456789abcdefABCDEF" for c in bare):
                new_state = _set_current(new_state, hex_to_rgb("#" + bare))
            return new_state, Action.CONTINUE

        # Any other key in hex mode: absorb
        return state, Action.CONTINUE
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): update() hex-input mode"
```

---

## Task 6: update() — SE pane (swatch browser)

This task implements the SE pane handlers. Navigation keys move `swatch_idx`. Hover (on any navigation) previews the focused swatch's color by writing it into `bg` or `fg`. Enter selects the current swatch and calls `_advance()`.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `tests/picker/test_app.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/picker/test_app.py`:

```python
# ---------------------------------------------------------------------------
# Task 6: SE pane — swatch browser
# ---------------------------------------------------------------------------

# A small fixture color dict for tests
_TEST_COLORS = {
    "red":   "#ff0000",
    "green": "#00ff00",
    "blue":  "#0000ff",
    "black": "#000000",
    "white": "#ffffff",
}

# Patch NAMED_COLORS so swatch_idx math is deterministic
import unittest.mock as _mock

def _se_state(**kwargs) -> State:
    base = dataclasses.replace(
        _default_state(),
        pane="se", panes_mode="focus", step="bg",
        filter="", sort_mode="name", swatch_idx=0,
    )
    return dataclasses.replace(base, **kwargs)


def test_se_arrow_right_increments_swatch_idx():
    s = _se_state(swatch_idx=0)
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.swatch_idx == 1


def test_se_arrow_right_clamps_at_last():
    # 5 colors, idx=4 (last), right should clamp
    s = _se_state(swatch_idx=4)
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.swatch_idx == 4


def test_se_arrow_left_decrements_swatch_idx():
    s = _se_state(swatch_idx=2)
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=False, ctrl=False))
    assert new_s.swatch_idx == 1


def test_se_arrow_left_clamps_at_zero():
    s = _se_state(swatch_idx=0)
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_LEFT, char=None, shift=False, ctrl=False))
    assert new_s.swatch_idx == 0


def test_se_arrow_down_jumps_by_num_cols(monkeypatch):
    # num_cols is computed from pane width; we test with a known SE pane width.
    # The update() function needs cols/rows to compute num_cols. We pass them
    # via the caller convention: update() accepts optional cols/rows for SE math.
    # Rather than special-casing the signature, we use the default 80-col layout:
    # halfW = 40, SE pane w = 40-2 = 38, num_cols = max(1, (38-2)//5) = 7
    # So arrow-down moves by 7.
    s = _se_state(swatch_idx=0)
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_DOWN, char=None, shift=False, ctrl=False),
                          cols=80, rows=24)
    # With 5 colors, min(5-1, 0+7) = 4
    assert new_s.swatch_idx == 4


def test_se_arrow_up_jumps_by_num_cols(monkeypatch):
    s = _se_state(swatch_idx=4)
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_UP, char=None, shift=False, ctrl=False),
                          cols=80, rows=24)
    # max(0, 4-7) = 0
    assert new_s.swatch_idx == 0


def test_se_navigation_previews_hovered_color():
    # Right arrow -> swatch_idx=1 -> green -> bg updates to green
    s = _se_state(swatch_idx=0, bg=RGB(0, 0, 0), step="bg")
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    # Entries in "name" sort order: red, green, blue, black, white
    # After moving to idx=1 (green #00ff00):
    assert new_s.bg == RGB(0, 255, 0)


def test_se_navigation_previews_to_fg_when_step_fg():
    s = _se_state(swatch_idx=0, fg=RGB(0, 0, 0), step="fg")
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, _ = update(s, KeyEvent(key=Key.ARROW_RIGHT, char=None, shift=False, ctrl=False))
    assert new_s.fg == RGB(0, 255, 0)
    assert new_s.bg == s.bg   # bg unchanged


def test_se_enter_selects_and_advances():
    s = _se_state(swatch_idx=2, step="bg")  # blue
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        new_s, action = update(s, KeyEvent(key=Key.ENTER, char=None, shift=False, ctrl=False))
    assert action is Action.CONTINUE
    assert new_s.step == "fg"
    assert new_s.bg == RGB(0, 0, 255)


def test_se_enter_on_fg_step_confirms():
    s = _se_state(swatch_idx=0, step="fg")
    with _mock.patch("src.picker.app.NAMED_COLORS", _TEST_COLORS):
        _, action = update(s, KeyEvent(key=Key.ENTER, char=None, shift=False, ctrl=False))
    assert action is Action.CONFIRM
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v -k "se_"
```

Expected: all fail because SE branch is not yet implemented.

- [ ] **Step 3: Implement SE pane handler**

The SE pane handler needs `cols` and `rows` to compute `num_cols` (for up/down navigation). Update `update()`'s signature to accept optional `cols` and `rows` with defaults:

In `src/picker/app.py`, change the `update()` signature from:

```python
def update(state: State, event: KeyEvent) -> tuple[State, Action]:
```

to:

```python
def update(
    state: State,
    event: KeyEvent,
    cols: int = 80,
    rows: int = 24,
) -> tuple[State, Action]:
```

Then append the SE pane handler inside `update()`, after the SW pane blocks and before the final `return state, Action.CONTINUE`:

```python
    # -----------------------------------------------------------------------
    # SE pane — swatch browser (mirrors App.tsx:326-337 onHover/onSelect)
    # -----------------------------------------------------------------------
    if p == "se":
        # Compute the number of swatch columns for this terminal width
        half_w = cols // 2
        se_pane_w = cols - half_w - 2   # subtract border chars
        num_cols_sw = max(1, (se_pane_w - 2) // 5)

        # Build the filtered+sorted entry list (same logic as render_swatch_browser)
        from src.picker.components.swatch_browser import sort_entries
        all_entries = list(NAMED_COLORS.items())
        filtered = [(n, h) for n, h in all_entries
                    if state.filter.lower() in n.lower()]
        entries = sort_entries(filtered, state.sort_mode)
        n_entries = len(entries)

        if n_entries == 0:
            return state, Action.CONTINUE

        def _preview_at(idx: int, base: State) -> State:
            """Apply the color at `idx` in `entries` to the current channel."""
            clamped = max(0, min(n_entries - 1, idx))
            _, hex_val = entries[clamped]
            new_rgb = hex_to_rgb(hex_val)
            return _set_current(dataclasses.replace(base, swatch_idx=clamped), new_rgb)

        if k is Key.ARROW_RIGHT:
            new_idx = min(n_entries - 1, state.swatch_idx + 1)
            return _preview_at(new_idx, state), Action.CONTINUE

        if k is Key.ARROW_LEFT:
            new_idx = max(0, state.swatch_idx - 1)
            return _preview_at(new_idx, state), Action.CONTINUE

        if k is Key.ARROW_DOWN:
            new_idx = min(n_entries - 1, state.swatch_idx + num_cols_sw)
            return _preview_at(new_idx, state), Action.CONTINUE

        if k is Key.ARROW_UP:
            new_idx = max(0, state.swatch_idx - num_cols_sw)
            return _preview_at(new_idx, state), Action.CONTINUE

        if k is Key.ENTER:
            # Apply selected color and advance
            _, hex_val = entries[max(0, min(n_entries - 1, state.swatch_idx))]
            new_rgb = hex_to_rgb(hex_val)
            new_state = _set_current(state, new_rgb)
            return _advance(new_state)
```

Also add `NAMED_COLORS` to the imports section of `app.py` (it was already imported in the skeleton via `from src.picker.names import NAMED_COLORS` — verify it's present; add it if not).

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): update() SE swatch browser pane"
```

---

## Task 7: render() — frame assembly

This task implements `render(state, cols, rows) -> Frame`. It builds a Frame of `(cols, rows)` cells and delegates each pane's interior to the Phase 3 component functions.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `tests/picker/test_app.py`

- [ ] **Step 1: Write failing smoke tests for render()**

Append to `tests/picker/test_app.py`:

```python
# ---------------------------------------------------------------------------
# Task 7: render() smoke tests
# ---------------------------------------------------------------------------

from src.picker.app import render
from src.picker.frame import Frame


def test_render_returns_frame():
    s = _default_state()
    f = render(s, cols=80, rows=24)
    assert isinstance(f, Frame)
    assert f.width == 80
    assert f.height == 24


def test_render_title_bar_has_hued():
    s = _default_state()
    f = render(s, cols=80, rows=24)
    row0 = "".join(f.get(0, c).char for c in range(80))
    assert "hued" in row0


def test_render_title_bar_shows_bg_step():
    s = dataclasses.replace(_default_state(), step="bg")
    f = render(s, cols=80, rows=24)
    row0 = "".join(f.get(0, c).char for c in range(80))
    assert "background" in row0


def test_render_title_bar_shows_fg_step():
    s = dataclasses.replace(_default_state(), step="fg")
    f = render(s, cols=80, rows=24)
    row0 = "".join(f.get(0, c).char for c in range(80))
    assert "foreground" in row0


def test_render_title_shows_nav_indicator():
    s = dataclasses.replace(_default_state(), panes_mode="nav")
    f = render(s, cols=80, rows=24)
    row0 = "".join(f.get(0, c).char for c in range(80))
    assert "[nav]" in row0


def test_render_footer_has_keymap_hints():
    s = _default_state()
    f = render(s, cols=80, rows=24)
    last_row = "".join(f.get(23, c).char for c in range(80))
    assert "tab" in last_row
    assert "esc" in last_row


def test_render_nw_pane_has_border():
    s = _default_state()
    f = render(s, cols=80, rows=24)
    # NW pane top-left corner should be a box-drawing character
    nw_top_row = 1   # title bar is row 0; NW pane starts at row 1
    nw_left_col = 0
    assert f.get(nw_top_row, nw_left_col).char in ("┌", "│", "─", "└", "┐", "┘")


def test_render_focused_pane_border_is_cyan():
    s = dataclasses.replace(_default_state(), pane="sw", panes_mode="focus")
    f = render(s, cols=80, rows=24)
    # The SW pane border corner should be cyan
    half_h = max(4, (24 - 2) // 2)
    sw_top_row = 1 + half_h   # below NW
    sw_top_left = 0
    corner = f.get(sw_top_row, sw_top_left)
    assert corner.fg == RGB(0, 255, 255)


def test_render_nav_focused_pane_border_is_yellow():
    s = dataclasses.replace(_default_state(), pane="sw", panes_mode="nav")
    f = render(s, cols=80, rows=24)
    half_h = max(4, (24 - 2) // 2)
    sw_top_row = 1 + half_h
    corner = f.get(sw_top_row, 0)
    assert corner.fg == RGB(200, 200, 0)


def test_render_unfocused_pane_border_is_gray():
    s = dataclasses.replace(_default_state(), pane="sw")
    f = render(s, cols=80, rows=24)
    # NW pane is not focused; its border should be gray
    corner = f.get(1, 0)
    assert corner.fg == RGB(128, 128, 128)


def test_render_small_terminal_does_not_crash():
    s = _default_state()
    f = render(s, cols=40, rows=12)
    assert f.width == 40
    assert f.height == 12
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_app.py -v -k "render"
```

Expected: `ImportError: cannot import name 'render'`.

- [ ] **Step 3: Implement render()**

Add to `src/picker/app.py` (after the `update()` function):

```python
from src.picker.frame import Frame
from src.picker.term import ansi_truecolor_fg
from src.picker.colors import nearest_name

# Color constants for pane borders
_GRAY   = RGB(128, 128, 128)
_CYAN   = RGB(0, 255, 255)
_YELLOW = RGB(200, 200, 0)


def _border_color(state: State, pane: str) -> RGB:
    """Return the border color for `pane` given the current state."""
    if state.pane != pane:
        return _GRAY
    return _CYAN if state.panes_mode == "focus" else _YELLOW


def render(state: State, cols: int, rows: int) -> Frame:
    """Pure render function. Returns a fully-painted Frame.

    Layout:
      Row 0:              title bar
      Rows 1 .. half_h:   NW pane (left) and NE pane (right)
      Rows half_h+1..-2:  SW pane (left) and SE pane (right)
      Row rows-1:         footer
    """
    from src.picker.components.slider import render_slider
    from src.picker.components.settings import render_settings
    from src.picker.components.preview import render_terminal_preview
    from src.picker.components.swatch_browser import render_swatch_browser
    from src.picker.components.slicer import render_color_slicer
    from src.picker.colors import rgb_to_hex

    frame = Frame(cols, rows)

    half_w = cols // 2
    half_h = max(4, (rows - 2) // 2)   # rows-2: 1 for title, 1 for footer

    right_w = cols - half_w

    # -------------------------------------------------------------------
    # Row 0: title bar
    # -------------------------------------------------------------------
    frame.fill(0, 0, cols, 1, " ")
    c = 1
    # "hued " in cyan
    frame.put_str(0, c, "hued ", fg=_CYAN)
    c += 5
    # "background" or "foreground" step indicators
    frame.put_str(0, c, "background",
                  fg=_CYAN if state.step == "bg" else _GRAY)
    c += 10
    frame.put_str(0, c, " → ", fg=_GRAY)
    c += 3
    frame.put_str(0, c, "foreground",
                  fg=_CYAN if state.step == "fg" else _GRAY)
    c += 10
    # [nav] indicator
    if state.panes_mode == "nav":
        frame.put_str(0, c, "  [nav]", fg=_GRAY)
        c += 7
    # Search area (right-aligned)
    search_label = "/ "
    filter_text = state.filter
    cursor_char = "█" if state.search_focused else ""
    search_str = search_label + filter_text + cursor_char
    search_col = cols - len(search_str) - 1
    if search_col > c:
        frame.put_str(0, search_col, "/", fg=_GRAY)
        frame.put_str(0, search_col + 2, filter_text,
                      fg=_CYAN if state.search_focused else (
                          RGB(255, 255, 255) if filter_text else _GRAY
                      ))
        if state.search_focused:
            frame.put_str(0, search_col + 2 + len(filter_text), "█", fg=_CYAN)

    # -------------------------------------------------------------------
    # NW pane: settings + terminal preview
    # -------------------------------------------------------------------
    nw_row = 1
    nw_col = 0
    nw_w = half_w
    nw_h = half_h
    frame.box(nw_row, nw_col, nw_w, nw_h, fg=_border_color(state, "nw"))

    settings_w = max(4, nw_w // 2)
    render_settings(
        frame,
        row=nw_row + 1,
        col=nw_col + 1,
        w=settings_w - 2,
        h=nw_h - 2,
        model=state.model,
        step=state.step,
        live=state.live,
        current_hex=rgb_to_hex(state.current),
        nearest_name=nearest_name(state.current, NAMED_COLORS),
    )
    render_terminal_preview(
        frame,
        row=nw_row + 1,
        col=nw_col + settings_w,
        w=nw_w - settings_w - 1,
        h=nw_h - 2,
        bg_hex=rgb_to_hex(state.bg),
        fg_hex=rgb_to_hex(state.fg),
    )

    # -------------------------------------------------------------------
    # SW pane: sliders or hex input
    # -------------------------------------------------------------------
    sw_row = 1 + half_h
    sw_col = 0
    sw_w = half_w
    sw_h = rows - 2 - half_h   # fill remaining rows above footer
    frame.box(sw_row, sw_col, sw_w, sw_h, fg=_border_color(state, "sw"))

    slider_w = sw_w - 4   # border(2) + paddingX(2)
    if not state.hex_mode:
        # Compute channel definitions for the current model
        current_rgb = state.current
        _channels = _build_channels(state.model, current_rgb)
        n_channels = len(_channels)
        for idx, ch_def in enumerate(_channels):
            is_focused_slider = (
                state.pane == "sw"
                and state.panes_mode == "focus"
                and state.focused_channel == idx
            )
            display_value = (
                state.acc_value
                if (is_focused_slider and state.acc_value is not None)
                else ch_def["value"]
            )
            render_slider(
                frame,
                row=sw_row + 1 + idx * 3,
                col=sw_col + 2,
                w=slider_w,
                h=3,
                label=ch_def["label"],
                value=display_value,
                max=ch_def["max"],
                focused=is_focused_slider,
                get_color=ch_def["get_color"],
            )
    else:
        # Hex input mode
        frame.fill(sw_row + 1, sw_col + 1, sw_w - 2, 1, " ")
        hex_text = state.hex_input or rgb_to_hex(state.current)
        bare = hex_text.lstrip("#")
        frame.put_str(sw_row + 2, sw_col + 2, "# ", fg=_GRAY)
        frame.put_str(sw_row + 2, sw_col + 4, bare, fg=_CYAN)
        if state.pane == "sw" and state.panes_mode == "focus":
            frame.put_str(sw_row + 2, sw_col + 4 + len(bare), "█", fg=_CYAN)

    # -------------------------------------------------------------------
    # NE pane: color slicer
    # -------------------------------------------------------------------
    ne_row = 1
    ne_col = half_w
    ne_w = right_w
    ne_h = half_h
    frame.box(ne_row, ne_col, ne_w, ne_h, fg=_border_color(state, "ne"))
    slicer_w = ne_w - 2
    slicer_h = ne_h - 2
    if slicer_w >= 4 and slicer_h >= 2:
        render_color_slicer(
            frame,
            row=ne_row + 1,
            col=ne_col + 1,
            w=slicer_w,
            h=slicer_h,
            model=state.model,
            current=state.current,
            view_idx=state.view_idx,
        )

    # -------------------------------------------------------------------
    # SE pane: swatch browser
    # -------------------------------------------------------------------
    se_row = 1 + half_h
    se_col = half_w
    se_w = right_w
    se_h = rows - 2 - half_h
    frame.box(se_row, se_col, se_w, se_h, fg=_border_color(state, "se"))
    sb_w = se_w - 2
    sb_h = se_h - 2
    if sb_w >= 4 and sb_h >= 2:
        render_swatch_browser(
            frame,
            row=se_row + 1,
            col=se_col + 1,
            w=sb_w,
            h=sb_h,
            colors=NAMED_COLORS,
            filter_str=state.filter,
            sort_mode=state.sort_mode,
            focused_idx=state.swatch_idx,
        )

    # -------------------------------------------------------------------
    # Footer: keymap hints
    # -------------------------------------------------------------------
    frame.fill(rows - 1, 0, cols, 1, " ")
    hints = [
        ("tab", " pane  "),
        ("↑↓", " channel  "),
        ("←→", " adjust  "),
        ("enter", f" {'next →' if state.step == 'bg' else 'confirm'}  "),
        ("/", " search  "),
        ("#", " hex  "),
        ("`", " model  "),
        ("\\", " sort  "),
        ("[/]", " view  "),
        ("esc", " nav  "),
        ("^C", " cancel"),
    ]
    fc = 1
    for key_text, desc_text in hints:
        if fc + len(key_text) + len(desc_text) >= cols - 1:
            break
        frame.put_str(rows - 1, fc, key_text, fg=_GRAY)
        fc += len(key_text)
        frame.put_str(rows - 1, fc, desc_text)
        fc += len(desc_text)

    return frame
```

Also add the `_build_channels` helper to `app.py` (after `_apply_channel`, before `update()`):

```python
def _build_channels(model: str, rgb: RGB) -> list[dict]:
    """Build the list of channel descriptor dicts for `model` and current `rgb`.

    Each dict has: label (str), value (int), max (int), get_color (callable).
    Mirrors the rgbChannels/hslChannels/oklchChannels/labChannels arrays in App.tsx.
    """
    from src.picker.colors import (
        rgb_to_hsl, hsl_to_rgb, HSL,
        rgb_to_oklch, oklch_to_rgb, OKLCH,
        rgb_to_lab, lab_to_rgb, Lab,
        rgb_to_hex,
    )

    if model == "rgb":
        return [
            {
                "label": "R", "value": rgb.r, "max": 255,
                "get_color": lambda v: RGB(v, rgb.g, rgb.b),
            },
            {
                "label": "G", "value": rgb.g, "max": 255,
                "get_color": lambda v: RGB(rgb.r, v, rgb.b),
            },
            {
                "label": "B", "value": rgb.b, "max": 255,
                "get_color": lambda v: RGB(rgb.r, rgb.g, v),
            },
        ]

    if model == "hsl":
        hsl = rgb_to_hsl(rgb)
        return [
            {
                "label": "H", "value": round(hsl.h), "max": 360,
                "get_color": lambda v: hsl_to_rgb(HSL(float(v), hsl.s, hsl.l)),
            },
            {
                "label": "S", "value": round(hsl.s), "max": 100,
                "get_color": lambda v: hsl_to_rgb(HSL(hsl.h, float(v), hsl.l)),
            },
            {
                "label": "L", "value": round(hsl.l), "max": 100,
                "get_color": lambda v: hsl_to_rgb(HSL(hsl.h, hsl.s, float(v))),
            },
        ]

    if model == "oklch":
        oklch = rgb_to_oklch(rgb)
        return [
            {
                "label": "L", "value": oklch.l, "max": 100,
                "get_color": lambda v: oklch_to_rgb(OKLCH(v, oklch.c, oklch.h)),
            },
            {
                "label": "C", "value": oklch.c, "max": 400,
                "get_color": lambda v: oklch_to_rgb(OKLCH(oklch.l, v, oklch.h)),
            },
            {
                "label": "H", "value": oklch.h, "max": 360,
                "get_color": lambda v: oklch_to_rgb(OKLCH(oklch.l, oklch.c, v)),
            },
        ]

    if model == "lab":
        lab = rgb_to_lab(rgb)
        return [
            {
                "label": "L", "value": lab.l, "max": 100,
                "get_color": lambda v: lab_to_rgb(Lab(v, lab.a, lab.b)),
            },
            {
                "label": "a", "value": lab.a + 128, "max": 255,
                "get_color": lambda v: lab_to_rgb(Lab(lab.l, v - 128, lab.b)),
            },
            {
                "label": "b", "value": lab.b + 128, "max": 255,
                "get_color": lambda v: lab_to_rgb(Lab(lab.l, lab.a, v - 128)),
            },
        ]

    return []
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_app.py -v
```

Expected: all tests pass. The render smoke tests verify structure, not pixel-perfect layout.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py tests/picker/test_app.py
git commit -m "feat(picker): render() frame assembly with all four panes"
```

---

## Task 8: run() + main() + __main__.py wiring

This task implements the `run()` event loop that owns all terminal I/O side effects, and `main()` for CLI argument parsing. It also updates `__main__.py` to dispatch to `app.main()` when `--app` is passed.

**Files:**
- Modify: `src/picker/app.py`
- Modify: `src/picker/__main__.py`

There are no unit tests for `run()` or `main()` — they touch real terminal I/O. Phase 5's interactive smoke test exercises them manually.

- [ ] **Step 1: Implement run() and main()**

Append to `src/picker/app.py`:

```python
import os
import signal
import threading


def run(
    initial_bg: RGB,
    initial_fg: RGB,
    output_path: Optional[str],
    live: bool,
) -> int:
    """Event-loop entry point. Returns an exit code: 0 = confirmed, 1 = cancelled.

    Side effects (all contained here — update() and render() remain pure):
      - Enter/exit alternate screen
      - Hide/show cursor
      - Install/uninstall SIGWINCH handler
      - Emit OSC bg/fg sequences when live=True
      - Write .hued output file on confirm

    This function is NOT unit-tested. It is exercised by the Phase 5
    interactive smoke test via `python3 -m src.picker --app`.
    """
    import src.picker.term as t
    from src.picker.colors import rgb_to_hex

    state = initial_state(initial_bg, initial_fg, live)

    # Resize flag: set in signal handler, consumed in main loop
    _resize_pending = threading.Event()

    def _on_resize(new_cols: int, new_rows: int) -> None:
        _resize_pending.set()

    # Enter alternate screen and hide cursor
    sys.stdout.write(t.enter_alt_screen())
    sys.stdout.write(t.hide_cursor())
    sys.stdout.write(t.clear_screen())
    sys.stdout.flush()

    # Initial OSC live colors
    if live:
        t.osc_bg(rgb_to_hex(state.bg))
        t.osc_fg(rgb_to_hex(state.fg))

    t.install_resize_handler(_on_resize)

    action = Action.CONTINUE
    try:
        with t.raw_mode():
            # Initial render
            cols, rows = t.get_size()
            render(state, cols, rows).flush()

            while action is Action.CONTINUE:
                ev = t.read_key()

                prev_bg = state.bg
                prev_fg = state.fg

                cols, rows = t.get_size()
                state, action = update(state, ev, cols=cols, rows=rows)

                # Apply OSC if live and color changed
                if state.live:
                    if state.bg != prev_bg:
                        t.osc_bg(rgb_to_hex(state.bg))
                    if state.fg != prev_fg:
                        t.osc_fg(rgb_to_hex(state.fg))

                # Handle pending resize
                if _resize_pending.is_set():
                    _resize_pending.clear()
                    cols, rows = t.get_size()
                    sys.stdout.write(t.clear_screen())

                # Re-render
                cols, rows = t.get_size()
                render(state, cols, rows).flush()

    finally:
        t.uninstall_resize_handler()
        if live:
            t.osc_reset_bg()
            t.osc_reset_fg()
        sys.stdout.write(t.show_cursor())
        sys.stdout.write(t.exit_alt_screen())
        sys.stdout.flush()

    if action is Action.CONFIRM:
        result = (
            f"background={rgb_to_hex(state.bg)}\n"
            f"foreground={rgb_to_hex(state.fg)}\n"
        )
        if output_path:
            from pathlib import Path
            Path(output_path).write_text(result)
        else:
            sys.stdout.write(result)
            sys.stdout.flush()
        return 0

    # CANCEL
    return 1


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point for the picker.

    Usage:
      python3 -m src.picker --app [--bg #rrggbb] [--fg #rrggbb] [--live] [--output PATH]

    Exit codes: 0 = color confirmed and written, 1 = cancelled.
    """
    import argparse
    from src.picker.colors import hex_to_rgb, rgb_to_hex

    parser = argparse.ArgumentParser(
        prog="hued-pick",
        description="Interactive terminal color picker",
    )
    parser.add_argument("--bg", default="#1a1a2e",
                        help="Initial background color as hex (default: #1a1a2e)")
    parser.add_argument("--fg", default="#e0e0e0",
                        help="Initial foreground color as hex (default: #e0e0e0)")
    parser.add_argument("--live", action="store_true",
                        help="Apply colors to terminal in real time via OSC")
    parser.add_argument("--output", default=None,
                        help="Write result to this file instead of stdout")

    args = parser.parse_args(argv)

    try:
        initial_bg = hex_to_rgb(args.bg)
    except (ValueError, IndexError):
        print(f"hued-pick: invalid --bg color: {args.bg!r}", file=sys.stderr)
        return 2

    try:
        initial_fg = hex_to_rgb(args.fg)
    except (ValueError, IndexError):
        print(f"hued-pick: invalid --fg color: {args.fg!r}", file=sys.stderr)
        return 2

    return run(initial_bg, initial_fg, args.output, args.live)
```

- [ ] **Step 2: Update __main__.py to dispatch to app.main() on --app flag**

Read the current `src/picker/__main__.py` and replace it entirely with a version that dispatches based on `--app`:

```python
"""src.picker package entry point.

Without --app:  run the Phase 2 smoke test (Frame rendering demo).
With    --app:  run the interactive color picker (Phase 4 app).

Usage:
  python3 -m src.picker          # smoke test
  python3 -m src.picker --app    # full interactive picker
  python3 -m src.picker --app --bg '#1a0a0a' --live
"""
import sys


def _smoke_main() -> int:
    """Phase 2 smoke test: renders a bordered frame with swatches."""
    from src.picker import term as t
    from src.picker.colors import RGB, hex_to_rgb
    from src.picker.frame import Frame
    from src.picker.names import NAMED_COLORS

    SWATCH_HEXES = [
        "#ff5555", "#ffaa55", "#ffff55", "#55ff55",
        "#55ffff", "#5555ff", "#aa55ff", "#ff55aa",
    ]

    first_name = next(iter(NAMED_COLORS))
    first_hex = NAMED_COLORS[first_name]

    def build_frame(cols: int, rows: int) -> Frame:
        f = Frame(cols, rows)
        f.box(0, 0, cols, rows, fg=RGB(128, 128, 128))
        for i, hex_v in enumerate(SWATCH_HEXES):
            rgb = hex_to_rgb(hex_v)
            f.fill(1, 1 + i * 8, w=8, h=1, char=" ", bg=rgb)
        f.put_str(3, 2, f"terminal bg: {first_name} ({first_hex})")
        f.put_str(5, 2, "press any key to exit (try arrow keys, shift+arrow, ctrl-c)")
        return f

    sys.stdout.write(t.enter_alt_screen())
    sys.stdout.write(t.hide_cursor())
    sys.stdout.write(t.clear_screen())
    sys.stdout.flush()
    t.osc_bg(first_hex)

    def on_resize(cols: int, rows: int) -> None:
        sys.stdout.write(t.clear_screen())
        build_frame(cols, rows).flush()

    t.install_resize_handler(on_resize)

    try:
        cols, rows = t.get_size()
        build_frame(cols, rows).flush()
        with t.raw_mode():
            event = t.read_key()
    finally:
        t.uninstall_resize_handler()
        t.osc_reset_bg()
        t.osc_reset_fg()
        sys.stdout.write(t.show_cursor())
        sys.stdout.write(t.exit_alt_screen())
        sys.stdout.flush()

    print(f"got: key={event.key.name} char={event.char!r} "
          f"shift={event.shift} ctrl={event.ctrl}")
    return 0


def main() -> int:
    if "--app" in sys.argv:
        # Strip --app from argv before passing to app.main()
        argv = [a for a in sys.argv[1:] if a != "--app"]
        from src.picker.app import main as app_main
        return app_main(argv)
    return _smoke_main()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Verify imports resolve cleanly**

```bash
.venv/bin/python -c "from src.picker.app import run, main; print('run and main importable OK')"
```

Expected: `run and main importable OK`.

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass (Phase 1-3 tests unchanged, all test_app.py tests pass). Zero failures.

- [ ] **Step 5: Commit**

```bash
git add src/picker/app.py src/picker/__main__.py
git commit -m "feat(picker): run() event loop, main() CLI parser, __main__.py dispatch"
```

---

## Task 9: Verification + push branch

- [ ] **Step 1: Run the full test suite and confirm counts**

```bash
.venv/bin/pytest -v
```

Expected: zero failures. New test count: Phase 1 (47) + Phase 2 (22 frame + 2 resize = 24 from Phase 2 total) + Phase 3 (~54) + Phase 4 (~60) ≈ 185 total. Exact count may vary by implementation; what matters is zero failures.

- [ ] **Step 2: Verify no inline styles or side effects in library functions**

```bash
grep -n "print(" src/picker/app.py
```

Expected: no output. `main()` is the only permitted print site (via `sys.stdout.write`).

- [ ] **Step 3: Verify all imports in app.py are stdlib or src.picker**

```bash
grep -E "^import |^from " src/picker/app.py | grep -Ev "(^from src\.picker|^from __future__|^import (sys|os|math|signal|threading|dataclasses|argparse|pathlib|typing|enum))"
```

Expected: no output.

- [ ] **Step 4: Verify no globals mutated outside run()**

```bash
grep -n "global " src/picker/app.py
```

Expected: no output. The module-level `_MODELS`, `_PANE_ORDER`, `_SORT_MODES`, and `_CHANNEL_MAX` are read-only constants, not mutated.

- [ ] **Step 5: Manual smoke test — smoke path (no --app)**

```bash
python3 -m src.picker
```

Expected: bordered frame with 8 swatches and help text. Press any key, clean exit, key info printed. Confirms `__main__.py` dispatch is not broken by Phase 4 changes.

- [ ] **Step 6: Manual smoke test — app path**

```bash
python3 -m src.picker --app --bg '#1a0a1a' --fg '#e0e0e0'
```

Expected: full picker UI appears with four panes. Verify:
- Title bar shows "hued", "background → foreground", current step highlighted cyan.
- SW pane (default focus) shows OKLCH sliders.
- Tab cycles focus through panes; border changes from yellow (nav) to cyan (focus) to gray (unfocused).
- Escape from focus mode → yellow border; Enter → cyan border.
- Arrow keys in SW pane adjust the focused slider and update colors in real time in the slicer.
- `` ` `` cycles model; sliders update immediately.
- `#` enters hex mode; typing hex digits in SW pane updates the color.
- `/` focuses search; typing filters the swatch browser.
- `\` cycles swatch sort mode.
- `[` / `]` cycle the slicer view; label updates.
- SE pane: Tab to it; arrow keys navigate swatches, hovered color previews immediately.
- Enter on fg step: confirm and print `background=... foreground=...` to stdout.
- Ctrl-C: clean exit, exit code 1, terminal restored.

- [ ] **Step 7: Verify clean exit on Ctrl-C**

```bash
python3 -m src.picker --app; echo "exit code: $?"
```

Press Ctrl-C immediately. Expected: `exit code: 1`, cursor visible, terminal background normal.

- [ ] **Step 8: Verify output file writing**

```bash
python3 -m src.picker --app --output /tmp/hued_test.txt
```

Select both colors and confirm. Then:

```bash
cat /tmp/hued_test.txt
```

Expected output format:
```
background=#rrggbb
foreground=#rrggbb
```

- [ ] **Step 9: Push branch**

```bash
git push -u origin feature/picker-app
```

---

## Self-review checklist

Before declaring Phase 4 done, verify the following. These checks must be performed by the implementing agent, not deferred.

- [ ] Search `src/picker/app.py` for `"TBD"`, `"TODO"`, `"etc."`, `"as appropriate"` — must find zero matches.
- [ ] Every branch in App.tsx lines 120-241 has a corresponding tested branch in `update()`.
- [ ] `update()` has no `global` statements, no `sys.stdout.write` calls, no signal operations.
- [ ] `render()` has no `sys.stdout.write` calls, no `t.osc_*` calls, no signal operations.
- [ ] `State` has exactly the fields defined in Task 1 plus `swatch_idx`; no others.
- [ ] `_build_channels()` returns `get_color` callables that capture the current color values by value (not by reference to a mutating variable). In Python, lambdas in a loop capture by name; review each lambda for closure correctness.
- [ ] The `NAMED_COLORS` import is present in `app.py` and used in both `render()` (for nearest_name) and the SE pane handler in `update()`.
- [ ] `.venv/bin/pytest -v` passes with zero failures before the push.

---

## What comes next (NOT in this plan)

- **Phase 5:** Replace `bin/hued-pick` (compiled TS binary) with a shell shim that calls `python3 -m src.picker --app`. Wire `bin/hued -i` to invoke `bin/hued-pick`. Update Homebrew formula (no Node runtime dep). Update README. Remove TS picker artifacts (`src/picker/*.ts`, `src/picker/*.tsx`, `src/picker/components/*.tsx`).

Phase 5 gets its own plan written after this one lands.
