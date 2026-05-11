from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.preview import render_terminal_preview


def _frame(w=30, h=12):
    return Frame(w, h)


def test_preview_box_top_left_corner():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    assert f.get(0, 0).char == "┌"


def test_preview_box_top_right_corner():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    assert f.get(0, 29).char == "┐"


def test_preview_interior_has_bg_color():
    f = _frame()
    bg = RGB(30, 30, 80)
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#1e1e50", fg_hex="#ffffff")
    # Interior starts at row 1, col 1 inside the box
    assert f.get(1, 1).bg == bg


def test_preview_interior_text_has_fg_color():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#00ff00")
    # Row 1 has the first sample text line with the fg color
    assert f.get(1, 2).fg == RGB(0, 255, 0)


def test_preview_sample_text_present():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    # "~/project" must appear somewhere on interior row 1
    row1 = "".join(f.get(1, c).char for c in range(30))
    assert "~/project" in row1


def test_preview_contrast_ratio_line_appears():
    f = _frame()
    # Black bg, white fg -> very high contrast
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    # Ratio line is at row 7 (box rows 0-5, blank row 6, ratio row 7)
    row7 = "".join(f.get(7, c).char for c in range(30))
    assert ":1" in row7


def test_preview_aa_pass_green_for_high_contrast():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    # "AA✓" should appear on the ratio line
    row7 = "".join(f.get(7, c).char for c in range(30))
    assert "AA✓" in row7


def test_preview_aa_fail_for_low_contrast():
    f = _frame()
    # Very similar colors -> fails AA (ratio << 4.5)
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#888888", fg_hex="#999999")
    row7 = "".join(f.get(7, c).char for c in range(30))
    assert "AA✗" in row7


def test_preview_hex_line_shows_both_hexes():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#1a2b3c", fg_hex="#eeddcc")
    row8 = "".join(f.get(8, c).char for c in range(30))
    assert "#1a2b3c" in row8
    assert "#eeddcc" in row8


def test_preview_col_offset():
    f = Frame(40, 12)
    render_terminal_preview(f, row=0, col=5, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    assert f.get(0, 5).char == "┌"
    assert f.get(0, 0).char == " "  # untouched
