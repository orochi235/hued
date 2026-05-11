import math
from src.picker.frame import Frame
from src.picker.colors import RGB, rgb_to_hsl, rgb_to_oklch, rgb_to_lab
from src.picker.components.slicer import (
    render_color_slicer, VIEWS, _clear_slicer_cache,
)

# Use a small frame for speed
_W, _H = 20, 10


def _frame():
    return Frame(_W, _H)


def setup_function():
    _clear_slicer_cache()


def test_render_does_not_crash():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(128, 64, 32), view_idx=0)


def test_label_appears_on_last_row():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(128, 64, 32), view_idx=0)
    # Label row is h-1 from the component row
    label_row = _H - 1
    row_text = "".join(f.get(label_row, c).char for c in range(_W))
    # RGB view 0 label should mention "R/G" and "B="
    assert "R/G" in row_text or "B=" in row_text


def test_cells_have_half_block_char():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(200, 100, 50), view_idx=0)
    # Most grid cells should contain ▀ (some corner cells might be out-of-gamut but still ▀)
    half_block_count = sum(
        1 for r in range(_H - 1) for c in range(_W)
        if f.get(r, c).char == "▀"
    )
    assert half_block_count > (_W * (_H - 1)) // 2


def test_cells_have_fg_and_bg():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="hsl", current=RGB(128, 64, 32), view_idx=0)
    # A grid cell should have both fg and bg set (both are RGB values)
    # Grid starts at row+1 (row 0 is margin)
    cell = f.get(1, 0)
    assert cell.fg is not None
    assert cell.bg is not None


def test_view_idx_wraps():
    f = _frame()
    # rgb has 3 views; view_idx=3 should wrap to view 0
    f2 = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(100, 100, 100), view_idx=0)
    render_color_slicer(f2, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(100, 100, 100), view_idx=3)
    # Both frames should be identical (same view)
    for r in range(_H):
        for c in range(_W):
            assert f.get(r, c) == f2.get(r, c), f"mismatch at ({r},{c})"


def test_all_models_render():
    for model in ("rgb", "hsl", "oklch", "lab"):
        f = _frame()
        render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                            model=model, current=RGB(100, 150, 200), view_idx=0)
        # Must paint at least one non-default cell
        non_default = sum(
            1 for r in range(_H) for c in range(_W)
            if f.get(r, c).char != " "
        )
        assert non_default > 0, f"model {model!r} painted nothing"


def test_cursor_marker_present():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(128, 0, 0), view_idx=0)
    # ◆ should appear somewhere in the slicer area (rows 0..h-2)
    marker_found = any(
        f.get(r, c).char == "◆"
        for r in range(_H - 1)
        for c in range(_W)
    )
    assert marker_found


def test_oklch_view_count():
    assert len(VIEWS["oklch"]) == 4


def test_hsl_view_count():
    assert len(VIEWS["hsl"]) == 4


def test_rgb_view_count():
    assert len(VIEWS["rgb"]) == 3


def test_lab_view_count():
    assert len(VIEWS["lab"]) == 4


def test_row_col_offset():
    f = Frame(30, 15)
    render_color_slicer(f, row=2, col=5, w=20, h=10,
                        model="rgb", current=RGB(100, 100, 100), view_idx=0)
    # Row 0, col 0 should be untouched
    assert f.get(0, 0).char == " "
    # Grid starts at row+1, so row 3, col 5 should be painted with ▀
    assert f.get(3, 5).char == "▀"
