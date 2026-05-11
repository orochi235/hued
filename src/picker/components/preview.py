from __future__ import annotations
import math
from src.picker.frame import Frame
from src.picker.colors import RGB, hex_to_rgb

_CYAN = RGB(0, 255, 255)
_DIM = RGB(128, 128, 128)
_GREEN = RGB(0, 200, 0)
_YELLOW = RGB(200, 200, 0)
_RED = RGB(200, 0, 0)

_SAMPLE_LINES = [
    "~/project",
    "$ git status",
    "On branch main",
    "$",
]


def _relative_luminance(rgb: RGB) -> float:
    """WCAG 2.1 relative luminance for an sRGB color."""
    def lin(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(rgb.r) + 0.7152 * lin(rgb.g) + 0.0722 * lin(rgb.b)


def _contrast_ratio(rgb1: RGB, rgb2: RGB) -> float:
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def render_terminal_preview(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    bg_hex: str,
    fg_hex: str,
) -> None:
    """Paint a simulated terminal preview into `frame` at (row, col, w, h).

    Layout (rows relative to `row`):
      row+0..row+5:  single-line box with 4 sample text rows inside
      row+6:         blank
      row+7:         contrast ratio line  e.g.  21.0:1  AA✓  AAA✓
      row+8:         bg #hex  fg #hex
    """
    bg_rgb = hex_to_rgb(bg_hex)
    fg_rgb = hex_to_rgb(fg_hex)

    # Box: occupies rows 0-5, full width
    box_h = 6
    frame.box(row, col, w, box_h, fg=_DIM)

    # Interior: rows 1-4 (inside the box), cols col+1..col+w-2
    inner_w = max(0, w - 2)
    for r_off, line in enumerate(_SAMPLE_LINES):
        r = row + 1 + r_off
        # Fill whole interior row with the bg color first
        frame.fill(r, col + 1, inner_w, 1, " ", bg=bg_rgb)
        # Prepend a space for left padding inside the box
        text = " " + line
        frame.put_str(r, col + 1, text[:inner_w], fg=fg_rgb, bg=bg_rgb)

    # Row 6: blank
    frame.fill(row + 6, col, w, 1, " ")

    # Row 7: contrast ratio + WCAG badges
    ratio = _contrast_ratio(bg_rgb, fg_rgb)
    ratio_str = f"{ratio:.1f}:1"
    aa = ratio >= 4.5
    aaa = ratio >= 7.0
    aa_badge = "AA✓" if aa else "AA✗"
    aaa_badge = "AAA✓" if aaa else "AAA✗"
    aa_fg = _GREEN if aa else _RED
    aaa_fg = _GREEN if aaa else _DIM
    ratio_fg = _GREEN if aa else _YELLOW

    frame.fill(row + 7, col, w, 1, " ")
    c = col + 1
    frame.put_str(row + 7, c, ratio_str, fg=ratio_fg)
    c += len(ratio_str) + 2
    frame.put_str(row + 7, c, aa_badge, fg=aa_fg)
    c += len(aa_badge) + 2
    frame.put_str(row + 7, c, aaa_badge, fg=aaa_fg)

    # Row 8: bg/fg hex values
    frame.fill(row + 8, col, w, 1, " ")
    c = col + 1
    frame.put_str(row + 8, c, "bg ", fg=_DIM)
    c += 3
    frame.put_str(row + 8, c, bg_hex, fg=_CYAN)
    c += len(bg_hex) + 2
    frame.put_str(row + 8, c, "fg ", fg=_DIM)
    c += 3
    frame.put_str(row + 8, c, fg_hex, fg=_CYAN)
