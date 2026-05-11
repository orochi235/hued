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


def update(state: State, event: KeyEvent) -> tuple[State, Action]:
    """Pure state transition function. Takes current State and a KeyEvent;
    returns (new_state, action). Never mutates state.

    Mirrors the TS useInput handler in App.tsx:120-241 branch-for-branch.
    """
    # All branches are implemented in Tasks 3-7.
    # Unknown keys: no-op.
    return state, Action.CONTINUE
