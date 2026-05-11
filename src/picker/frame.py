from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import IO, Optional

from src.picker.colors import RGB
from src.picker.term import (
    ansi_truecolor_bg,
    ansi_truecolor_fg,
    ansi_reset,
    cursor_to,
)


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

    def put_cell(
        self,
        row: int,
        col: int,
        char: str,
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        if not (0 <= row < self.height and 0 <= col < self.width):
            return
        self._cells[row][col] = Cell(char, fg, bg)

    def put_str(
        self,
        row: int,
        col: int,
        s: str,
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        if not (0 <= row < self.height):
            return
        for i, ch in enumerate(s):
            c = col + i
            if 0 <= c < self.width:
                self._cells[row][c] = Cell(ch, fg, bg)

    def fill(
        self,
        row: int,
        col: int,
        w: int,
        h: int,
        char: str = " ",
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        for r in range(row, row + h):
            if not (0 <= r < self.height):
                continue
            for c in range(col, col + w):
                if not (0 <= c < self.width):
                    continue
                self._cells[r][c] = Cell(char, fg, bg)

    def render(self) -> str:
        """Build the full frame as one ANSI string. Caller writes + flushes."""
        parts: list[str] = []
        for r in range(self.height):
            parts.append(cursor_to(r + 1, 1))
            parts.append(ansi_reset())
            last_fg: Optional[RGB] = None
            last_bg: Optional[RGB] = None
            for c in range(self.width):
                cell = self._cells[r][c]
                if cell.fg != last_fg:
                    parts.append(
                        ansi_truecolor_fg(cell.fg.r, cell.fg.g, cell.fg.b)
                        if cell.fg is not None
                        else ansi_reset()
                    )
                    last_fg = cell.fg
                    if cell.fg is None:
                        last_bg = None
                if cell.bg != last_bg:
                    if cell.bg is not None:
                        parts.append(ansi_truecolor_bg(cell.bg.r, cell.bg.g, cell.bg.b))
                    last_bg = cell.bg
                parts.append(cell.char)
        parts.append(ansi_reset())
        return "".join(parts)

    def flush(self, stream: IO[str] = sys.stdout) -> None:
        stream.write(self.render())
        stream.flush()

    def box(
        self,
        row: int,
        col: int,
        w: int,
        h: int,
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        """Draw a single-line box border. Interior cells are left untouched."""
        if w < 1 or h < 1:
            return
        self.put_cell(row, col, "┌", fg, bg)
        self.put_cell(row, col + w - 1, "┐", fg, bg)
        self.put_cell(row + h - 1, col, "└", fg, bg)
        self.put_cell(row + h - 1, col + w - 1, "┘", fg, bg)
        for c in range(col + 1, col + w - 1):
            self.put_cell(row, c, "─", fg, bg)
            self.put_cell(row + h - 1, c, "─", fg, bg)
        for r in range(row + 1, row + h - 1):
            self.put_cell(r, col, "│", fg, bg)
            self.put_cell(r, col + w - 1, "│", fg, bg)
