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
