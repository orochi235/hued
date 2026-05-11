from __future__ import annotations
import builtins
from typing import Callable, Optional
from src.picker.frame import Frame
from src.picker.colors import RGB

LABEL_W = 2   # "R " — label is padded/truncated to this width
VALUE_W = 4   # " 123" — right-aligned value, 4 chars wide
SHADOW_RGB = RGB(26, 26, 26)  # #1a1a1a


def _luma(rgb: RGB) -> float:
    return 0.299 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _contrast(bg: RGB) -> RGB:
    """Return black or white for readable text on `bg`."""
    return RGB(0, 0, 0) if _luma(bg) > 128 else RGB(255, 255, 255)


def render_slider(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    label: str,
    value: int,
    max: int,
    focused: bool = False,
    track_color: RGB = RGB(255, 255, 255),
    get_color: Optional[Callable[[int], RGB]] = None,
) -> None:
    """Paint a single-channel slider into `frame` at (row, col, w, h).

    With `get_color` supplied the slider renders 3 rows:
      Row 0: label + gradient track with ◆ marker at current value + right-aligned value
      Row 1: blank label + plain gradient track + one shadow cell to the right
      Row 2: blank (LABEL_W+1 chars) + shadow strip (track_w wide)

    Without `get_color` the slider renders 1 row using █/░ fill characters.
    The `h` parameter is accepted for interface uniformity but does not expand the
    component beyond its natural height — excess rows are simply unused.

    All out-of-bounds paints are silently clipped by Frame.
    """
    track_w = builtins.max(4, w - LABEL_W - VALUE_W)
    # Position of the marker (0-indexed within the track)
    pos = round((value / max) * (track_w - 1)) if max > 0 else 0

    accent = RGB(0, 255, 255) if focused else RGB(128, 128, 128)
    label_str = (label + " " * LABEL_W)[:LABEL_W]
    value_str = str(value).rjust(VALUE_W)

    if get_color is not None:
        # --- Row 0: label + track + value ---
        frame.put_str(row, col, label_str, fg=accent)
        for i in range(track_w):
            cell_val = round((i / (track_w - 1)) * max) if track_w > 1 else value
            bg = get_color(cell_val)
            char = "◆" if (i == pos and focused) else " "
            fg = _contrast(bg) if (i == pos and focused) else bg
            frame.put_cell(row, col + LABEL_W + i, char, fg=fg, bg=bg)
        frame.put_str(row, col + LABEL_W + track_w, value_str, fg=accent)

        # --- Row 1: blank label + plain track + shadow cell ---
        frame.put_str(row + 1, col, " " * LABEL_W)
        for i in range(track_w):
            cell_val = round((i / (track_w - 1)) * max) if track_w > 1 else value
            bg = get_color(cell_val)
            frame.put_cell(row + 1, col + LABEL_W + i, " ", bg=bg)
        # Shadow cell at track_w (just past end of track)
        frame.put_cell(row + 1, col + LABEL_W + track_w, " ", bg=SHADOW_RGB)
        # Fill remainder of value area with spaces
        frame.put_str(row + 1, col + LABEL_W + track_w + 1, " " * (VALUE_W - 1))

        # --- Row 2: wide shadow strip ---
        frame.put_str(row + 2, col, " " * (LABEL_W + 1))
        frame.fill(row + 2, col + LABEL_W + 1, track_w, 1, " ", bg=SHADOW_RGB)
        frame.put_str(row + 2, col + LABEL_W + 1 + track_w, " " * (VALUE_W - 1))

    else:
        # Fallback: 1-row block-bar
        frame.put_str(row, col, label_str, fg=accent)
        filled = round((value / max) * track_w) if max > 0 else 0
        frame.put_str(row, col + LABEL_W, "█" * filled,
                      fg=track_color if focused else RGB(128, 128, 128))
        frame.put_str(row, col + LABEL_W + filled, "░" * (track_w - filled),
                      fg=RGB(64, 64, 64))
        frame.put_str(row, col + LABEL_W + track_w, value_str, fg=accent)
