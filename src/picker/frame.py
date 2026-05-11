from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.picker.colors import RGB


@dataclass(frozen=True)
class Cell:
    char: str = " "
    fg: Optional[RGB] = None
    bg: Optional[RGB] = None


class Frame:
    """In-memory 2D grid of Cells; emits ANSI text via render()."""

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Frame dimensions must be positive, got {width}x{height}")
        self.width = width
        self.height = height
        self._cells: list[list[Cell]] = [
            [Cell() for _ in range(width)] for _ in range(height)
        ]

    def get(self, row: int, col: int) -> Cell:
        return self._cells[row][col]
