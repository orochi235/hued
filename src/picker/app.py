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


def update(
    state: State,
    event: KeyEvent,
    cols: int = 80,
    rows: int = 24,
) -> tuple[State, Action]:
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
        # In hex mode, ESC exits hex mode instead of switching to nav
        if state.hex_mode:
            return dataclasses.replace(
                state, hex_mode=False, hex_input=""
            ), Action.CONTINUE
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
    # SW pane — hex-input mode (hex_mode=True) (mirrors App.tsx:221-234)
    # -----------------------------------------------------------------------
    if p == "sw" and state.hex_mode:
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

    # All other keys in focus mode: no-op
    return state, Action.CONTINUE
