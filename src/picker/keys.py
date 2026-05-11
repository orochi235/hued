from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class Key(Enum):
    CHAR = auto()
    ARROW_UP = auto()
    ARROW_DOWN = auto()
    ARROW_LEFT = auto()
    ARROW_RIGHT = auto()
    ENTER = auto()
    TAB = auto()
    ESC = auto()
    BACKSPACE = auto()
    DELETE = auto()
    CTRL_C = auto()
    CTRL_L = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class KeyEvent:
    key: Key
    char: Optional[str]
    shift: bool
    ctrl: bool
