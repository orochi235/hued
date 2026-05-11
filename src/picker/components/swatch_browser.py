from __future__ import annotations
import math
from typing import List, Tuple
from src.picker.frame import Frame
from src.picker.colors import RGB, hex_to_rgb, rgb_to_hsl

_CYAN = RGB(0, 255, 255)
_DIM = RGB(128, 128, 128)
_YELLOW = RGB(200, 200, 0)

SortMode = str  # "name" | "hue"


def _luma(rgb: RGB) -> float:
    return 0.299 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _contrast(bg: RGB) -> RGB:
    return RGB(0, 0, 0) if _luma(bg) > 128 else RGB(255, 255, 255)


def sort_entries(
    entries: List[Tuple[str, str]],
    mode: SortMode,
) -> List[Tuple[str, str]]:
    """Sort (name, hex) pairs by `mode`.

    mode="name": return in original order (NAMED_COLORS is already alphabetical).
    mode="hue":  near-achromatic (HSL saturation < 5) sorted by lightness first,
                 then remaining sorted by hue, then saturation, then lightness.
    """
    if mode == "name":
        return list(entries)

    if mode == "hue":
        def hue_key(item: Tuple[str, str]):
            _, hex_val = item
            hsl = rgb_to_hsl(hex_to_rgb(hex_val))
            if hsl.s < 5:
                # Achromatic: sort before hued colors, by lightness
                return (0, hsl.l, 0.0, 0.0)
            return (1, hsl.h, hsl.s, hsl.l)
        return sorted(entries, key=hue_key)

    return list(entries)


def render_swatch_browser(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    colors: dict[str, str],
    filter_str: str,
    sort_mode: SortMode,
    focused_idx: int,
) -> None:
    """Paint a scrollable color swatch grid into `frame` at (row, col, w, h).

    Each swatch is 4 characters wide, with a 1-char gap between swatches and
    1-char left padding. Each swatch occupies 2 terminal rows. The bottom row
    of the component area is a status line showing the focused color name and hex.

    `focused_idx` is an index into the filtered+sorted color list. The caller
    is responsible for clamping it to the valid range before calling.
    """
    # 1. Filter
    filtered = [(n, h) for n, h in colors.items()
                if filter_str.lower() in n.lower()]

    # 2. Sort
    entries = sort_entries(filtered, sort_mode)

    # 3. Layout
    num_cols = max(1, (w - 2) // 5)  # each swatch+gap is 5 wide; 2 chars padding
    # Each swatch is 2 terminal rows tall; leave 1 row for status line
    visible_rows = max(1, (h - 1) // 2)

    if not entries:
        frame.fill(row, col, w, h, " ")
        frame.put_str(row, col + 1, "no results", fg=_DIM)
        return

    # 4. Scroll
    focused_clamped = max(0, min(focused_idx, len(entries) - 1))
    focused_row_in_grid = focused_clamped // num_cols
    total_rows = math.ceil(len(entries) / num_cols)
    scroll_row = max(0, min(focused_row_in_grid, total_rows - visible_rows))

    # 5. Paint swatch grid
    for vr in range(visible_rows):
        grid_row = scroll_row + vr
        row_entries_start = grid_row * num_cols
        row_entries = entries[row_entries_start: row_entries_start + num_cols]
        abs_row_top = row + vr * 2      # first terminal row of this swatch row
        abs_row_bot = abs_row_top + 1   # second terminal row (lower half of swatch)

        # Clear these two rows first
        frame.fill(abs_row_top, col, w, 1, " ")
        frame.fill(abs_row_bot, col, w, 1, " ")

        for ci, (name, hex_val) in enumerate(row_entries):
            abs_idx = grid_row * num_cols + ci
            is_focused = (abs_idx == focused_clamped)
            bg = hex_to_rgb(hex_val)
            swatch_col = col + 1 + ci * 5  # 1-char left pad, then 5 per swatch

            # Top row of swatch: show ◆ marker for focused
            for sc in range(4):
                if is_focused and sc == 0:
                    char = "◆"
                    fg = _contrast(bg)
                else:
                    char = " "
                    fg = bg  # invisible fg
                frame.put_cell(abs_row_top, swatch_col + sc, char, fg=fg, bg=bg)

            # Bottom row of swatch: plain fill
            frame.fill(abs_row_bot, swatch_col, 4, 1, " ", bg=bg)

    # 6. Status line: last row
    status_row = row + h - 1
    frame.fill(status_row, col, w, 1, " ")
    if 0 <= focused_clamped < len(entries):
        name, hex_val = entries[focused_clamped]
        frame.put_str(status_row, col + 1, name, fg=_CYAN)
        c = col + 1 + len(name) + 2
        frame.put_str(status_row, c, hex_val, fg=_DIM)
        c += len(hex_val) + 2
        frame.put_str(status_row, c, f"sort:{sort_mode}", fg=_DIM)
