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
                max_val=ch_def["max"],
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
        ("tab", " pane"),
        ("↑↓", " ch"),
        ("←→", " adj"),
        ("enter", f" {'next →' if state.step == 'bg' else 'confirm'}"),
        ("/", " search"),
        ("#", " hex"),
        ("`", " mdl"),
        ("\\", " srt"),
        ("[/]", " view"),
        ("esc", " nav"),
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
