from __future__ import annotations
import math
from typing import Callable, List, NamedTuple, Optional, Tuple

from src.picker.frame import Frame
from src.picker.colors import (
    RGB, HSL, OKLCH, Lab,
    rgb_to_hex, hex_to_rgb,
    rgb_to_hsl, hsl_to_rgb,
    rgb_to_oklch, oklch_to_rgb,
    rgb_to_lab, lab_to_rgb,
)

_OUT = RGB(17, 17, 17)  # #111111 — out-of-gamut / out-of-circle fill color

# Module-level cache: populated in Task 7.
_SLICER_CACHE: dict[tuple, list[list[tuple[RGB, RGB]]]] = {}


def _clear_slicer_cache() -> None:
    """Empty the slicer pixel cache. Call in test teardown."""
    _SLICER_CACHE.clear()


def _luma(rgb: RGB) -> float:
    return 0.299 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _contrast(rgb: RGB) -> RGB:
    return RGB(0, 0, 0) if _luma(rgb) > 128 else RGB(255, 255, 255)


def _polar(xn: float, yn: float) -> Tuple[float, float, bool]:
    """Convert normalized (xn, yn) to polar (r, theta, inside_circle).

    Origin is at the center of the unit square. yn=1 is visual top.
    r is in [0, 1] where 1 = edge of the inscribed circle.
    """
    dx = xn - 0.5
    dy = yn - 0.5  # positive y = upward (yn=1 is top)
    r = math.sqrt(dx * dx + dy * dy) / 0.5
    theta = math.atan2(dy, dx)
    return r, theta, r <= 1.0


def _polar_cursor(theta_rad: float, r: float) -> Tuple[float, float]:
    """Convert polar back to normalized (cxn, cyn). r is in [0,1] relative to circle radius."""
    return (
        0.5 + r * 0.5 * math.cos(theta_rad),
        0.5 - r * 0.5 * math.sin(theta_rad),  # yn: positive = upward
    )


# ---------------------------------------------------------------------------
# SlicerView definition
# ---------------------------------------------------------------------------

class SlicerView(NamedTuple):
    label: str  # short label shown below the slicer, e.g. "R/G  B=32"
    pixel_fn: Callable[[float, float], Optional[RGB]]  # (xn, yn) -> RGB or None
    cursor: Tuple[float, float]  # (cxn, cyn) — 0-indexed normalized cursor position


def _make_views(
    current: RGB,
    hsl: HSL,
    oklch: OKLCH,
    lab: Lab,
) -> dict[str, list[SlicerView]]:
    """Build the view list for every model given the current color values."""

    rgb = current

    return {
        "rgb": [
            SlicerView(
                label=f"R/G  B={rgb.b}",
                pixel_fn=lambda xn, yn: RGB(round(xn * 255), round(yn * 255), rgb.b),
                cursor=(rgb.r / 255, 1.0 - rgb.g / 255),
            ),
            SlicerView(
                label=f"R/B  G={rgb.g}",
                pixel_fn=lambda xn, yn: RGB(round(xn * 255), rgb.g, round(yn * 255)),
                cursor=(rgb.r / 255, 1.0 - rgb.b / 255),
            ),
            SlicerView(
                label=f"G/B  R={rgb.r}",
                pixel_fn=lambda xn, yn: RGB(rgb.r, round(xn * 255), round(yn * 255)),
                cursor=(rgb.g / 255, 1.0 - rgb.b / 255),
            ),
        ],
        "hsl": [
            SlicerView(
                label=f"H/S  L={round(hsl.l)}",
                pixel_fn=lambda xn, yn: hsl_to_rgb(HSL(xn * 360, yn * 100, hsl.l)),
                cursor=(hsl.h / 360, 1.0 - hsl.s / 100),
            ),
            SlicerView(
                label=f"H/L  S={round(hsl.s)}",
                pixel_fn=lambda xn, yn: hsl_to_rgb(HSL(xn * 360, hsl.s, yn * 100)),
                cursor=(hsl.h / 360, 1.0 - hsl.l / 100),
            ),
            SlicerView(
                label=f"S/L  H={round(hsl.h)}°",
                pixel_fn=lambda xn, yn: hsl_to_rgb(HSL(hsl.h, xn * 100, yn * 100)),
                cursor=(hsl.s / 100, 1.0 - hsl.l / 100),
            ),
            SlicerView(
                label=f"wheel  L={round(hsl.l)}",
                pixel_fn=lambda xn, yn: (
                    (lambda r, theta, inside:
                        hsl_to_rgb(HSL(
                            (math.degrees(theta) + 360) % 360,
                            r * 100,
                            hsl.l,
                        )) if inside else None
                    )(*_polar(xn, yn))
                ),
                cursor=_polar_cursor(math.radians(hsl.h), hsl.s / 100),
            ),
        ],
        "oklch": [
            SlicerView(
                label=f"H/C  L={oklch.l}",
                pixel_fn=lambda xn, yn: oklch_to_rgb(OKLCH(oklch.l, round(yn * 400), round(xn * 360))),
                cursor=(oklch.h / 360, 1.0 - oklch.c / 400),
            ),
            SlicerView(
                label=f"H/L  C={oklch.c}",
                pixel_fn=lambda xn, yn: oklch_to_rgb(OKLCH(round(yn * 100), oklch.c, round(xn * 360))),
                cursor=(oklch.h / 360, 1.0 - oklch.l / 100),
            ),
            SlicerView(
                label=f"C/L  H={oklch.h}°",
                pixel_fn=lambda xn, yn: oklch_to_rgb(OKLCH(round(yn * 100), round(xn * 400), oklch.h)),
                cursor=(oklch.c / 400, 1.0 - oklch.l / 100),
            ),
            SlicerView(
                label=f"wheel  L={oklch.l}",
                pixel_fn=lambda xn, yn: (
                    (lambda r, theta, inside:
                        oklch_to_rgb(OKLCH(
                            oklch.l,
                            round(r * 400),
                            round((math.degrees(theta) + 360) % 360),
                        )) if inside else None
                    )(*_polar(xn, yn))
                ),
                cursor=_polar_cursor(math.radians(oklch.h), oklch.c / 400),
            ),
        ],
        "lab": [
            SlicerView(
                label=f"a/b  L={lab.l}",
                pixel_fn=lambda xn, yn: lab_to_rgb(Lab(lab.l, round(xn * 255 - 128), round(yn * 255 - 128))),
                cursor=((lab.a + 128) / 255, 1.0 - (lab.b + 128) / 255),
            ),
            SlicerView(
                label=f"L/a  b={lab.b}",
                pixel_fn=lambda xn, yn: lab_to_rgb(Lab(round(xn * 100), round(yn * 255 - 128), lab.b)),
                cursor=(lab.l / 100, 1.0 - (lab.a + 128) / 255),
            ),
            SlicerView(
                label=f"L/b  a={lab.a}",
                pixel_fn=lambda xn, yn: lab_to_rgb(Lab(round(xn * 100), lab.a, round(yn * 255 - 128))),
                cursor=(lab.l / 100, 1.0 - (lab.b + 128) / 255),
            ),
            SlicerView(
                label=f"wheel  L={lab.l}",
                pixel_fn=lambda xn, yn: (
                    (lambda r, theta, inside:
                        lab_to_rgb(Lab(
                            lab.l,
                            round(math.cos(theta) * r * 128),
                            round(math.sin(theta) * r * 128),
                        )) if inside else None
                    )(*_polar(xn, yn))
                ),
                cursor=_polar_cursor(
                    math.atan2(lab.b, lab.a),
                    math.sqrt(lab.a * lab.a + lab.b * lab.b) / 128,
                ),
            ),
        ],
    }


# Expose VIEWS as a module-level constant so tests can inspect view counts.
# Built once at module load with a reference color; used only for len() queries.
# Per-render views are constructed fresh via _make_views(current, ...) each call.
_REF = RGB(128, 128, 128)
VIEWS: dict[str, list[SlicerView]] = _make_views(
    _REF, rgb_to_hsl(_REF), rgb_to_oklch(_REF), rgb_to_lab(_REF)
)


def _compute_pixel_grid(
    view: SlicerView,
    pixel_w: int,
    pixel_h: int,
) -> list[list[RGB]]:
    """Compute the full pixel_h x pixel_w grid of RGB values for `view`.

    Each entry is the color for that logical pixel. Out-of-gamut pixels
    (where pixel_fn returns None) use _OUT.
    """
    grid: list[list[RGB]] = []
    for py in range(pixel_h):
        row_pixels: list[RGB] = []
        yn = 1.0 - py / (pixel_h - 1) if pixel_h > 1 else 1.0
        for px in range(pixel_w):
            xn = px / (pixel_w - 1) if pixel_w > 1 else 0.0
            result = view.pixel_fn(xn, yn)
            row_pixels.append(result if result is not None else _OUT)
        grid.append(row_pixels)
    return grid


def _pair_rows(grid: list[list[RGB]]) -> list[list[tuple[RGB, RGB]]]:
    """Pair consecutive pixel rows into (top_rgb, bottom_rgb) tuples.

    Each pair becomes one terminal row of half-block cells.
    If the pixel grid has an odd number of rows, the last row is paired
    with _OUT as its bottom pixel.
    """
    paired: list[list[tuple[RGB, RGB]]] = []
    i = 0
    while i < len(grid):
        top_row = grid[i]
        bot_row = grid[i + 1] if (i + 1) < len(grid) else [_OUT] * len(top_row)
        paired.append(list(zip(top_row, bot_row)))
        i += 2
    return paired


def render_color_slicer(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    model: str,
    current: RGB,
    view_idx: int,
) -> None:
    """Paint a 2D color-space slice into `frame` at (row, col, w, h).

    Uses half-block characters (▀ U+2580): fg = top pixel, bg = bottom pixel.
    This doubles the effective vertical resolution — a component with h terminal
    rows shows h*2-2 logical pixel rows (h-1 terminal rows for pixels, 1 for label).

    The pixel grid is memoized in _SLICER_CACHE by (model, hex, view_idx, w, h).
    """
    hsl = rgb_to_hsl(current)
    oklch = rgb_to_oklch(current)
    lab = rgb_to_lab(current)

    all_views = _make_views(current, hsl, oklch, lab)
    view_list = all_views[model]
    view = view_list[view_idx % len(view_list)]

    pixel_w = max(1, w)
    grid_term_rows = max(1, h - 2)  # -1 for label row, -1 for top margin row
    pixel_h = grid_term_rows * 2    # two logical pixels per terminal row

    # Compute the pixel grid (memoized in Task 7; bare computation here)
    pixel_grid = _compute_pixel_grid(view, pixel_w, pixel_h)
    pairs = _pair_rows(pixel_grid)

    # Cursor position in pixel coordinates
    cxn, cyn = view.cursor
    cxn = max(0.0, min(1.0, cxn))
    cyn = max(0.0, min(1.0, cyn))
    cx = round(cxn * (pixel_w - 1)) if pixel_w > 1 else 0
    # cyn=1.0 is the top of the pixel grid (py=0), cyn=0.0 is py=pixel_h-1
    cy = round((1.0 - cyn) * (pixel_h - 1)) if pixel_h > 1 else 0
    cursor_term_row = cy // 2
    cursor_is_top = (cy % 2 == 0)

    # Paint one blank row at the top (row+0) as a margin
    frame.fill(row, col, w, 1, " ")

    # Paint half-block rows (start at row+1)
    for tr, pair_row in enumerate(pairs):
        abs_r = row + 1 + tr
        for pc, (top_rgb, bot_rgb) in enumerate(pair_row):
            is_cursor = (pc == cx and tr == cursor_term_row)
            if is_cursor:
                # Cursor ◆: draw in the appropriate half (top or bottom)
                if cursor_is_top:
                    marker_color = _contrast(top_rgb)
                    frame.put_cell(abs_r, col + pc, "◆",
                                   fg=marker_color, bg=bot_rgb)
                else:
                    marker_color = _contrast(bot_rgb)
                    # ◆ always goes in fg (upper half); swap top and bottom
                    # to keep the cursor in the bottom half visually
                    frame.put_cell(abs_r, col + pc, "▄",
                                   fg=marker_color, bg=top_rgb)
            else:
                frame.put_cell(abs_r, col + pc, "▀", fg=top_rgb, bg=bot_rgb)

    # Label row
    label_row = row + h - 1
    frame.fill(label_row, col, w, 1, " ")
    frame.put_str(label_row, col + 1, view.label, fg=RGB(128, 128, 128))
