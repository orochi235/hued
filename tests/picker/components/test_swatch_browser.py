from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.swatch_browser import render_swatch_browser, sort_entries


COLORS = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "black": "#000000",
    "white": "#ffffff",
}


def _frame(w=30, h=12):
    return Frame(w, h)


# --- sort_entries tests ---

def test_sort_name_preserves_order():
    entries = list(COLORS.items())
    result = sort_entries(entries, "name")
    assert [n for n, _ in result] == list(COLORS.keys())


def test_sort_hue_puts_achromatic_first():
    result = sort_entries(list(COLORS.items()), "hue")
    names = [n for n, _ in result]
    # black and white are achromatic (s < 5 in HSL); they must come before hued colors
    assert names.index("black") < names.index("red")
    assert names.index("white") < names.index("red")


def test_sort_hue_orders_hued_by_hue():
    result = sort_entries(list(COLORS.items()), "hue")
    # red (hue~0), green (hue~120), blue (hue~240)
    names = [n for n, _ in result]
    hued = [n for n in names if n not in ("black", "white")]
    assert hued.index("red") < hued.index("green") < hued.index("blue")


# --- render_swatch_browser tests ---

def test_swatch_browser_paints_swatch_bg():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # The first swatch (red) should start at col 1, rows 0-1 with bg RGB(255,0,0)
    cell = f.get(0, 1)
    assert cell.bg == RGB(255, 0, 0)


def test_swatch_browser_focused_marker():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # First swatch row 0 should contain ◆ somewhere in cols 1-4
    row0 = [f.get(0, c).char for c in range(1, 5)]
    assert "◆" in row0


def test_swatch_browser_no_marker_on_unfocused():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=1)
    # First swatch (idx 0) should NOT have ◆
    row0 = [f.get(0, c).char for c in range(1, 5)]
    assert "◆" not in row0


def test_swatch_browser_filter_reduces_items():
    f = _frame()
    # Only "red" matches "ed"
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="ed", sort_mode="name",
                          focused_idx=0)
    # Green swatch (bg #00ff00) should NOT appear — check a different col range
    # With only 1 match the second swatch position (cols 6-9) should be empty/default
    num_cols = max(1, (30 - 2) // 5)
    if num_cols >= 2:
        second_cell = f.get(0, 1 + 5)  # second swatch starts at col 6
        # It should not have bg RGB(0,255,0) because green was filtered out
        assert second_cell.bg != RGB(0, 255, 0)


def test_swatch_browser_status_line_shows_name():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # Status line is the last row used; find it by checking for "red" in the bottom rows
    found = False
    for r in range(10, 12):
        row_text = "".join(f.get(r, c).char for c in range(30))
        if "red" in row_text:
            found = True
            break
    assert found, "status line showing focused color name not found"


def test_swatch_browser_scroll_keeps_focused_visible():
    # With a tall-enough browser and many colors, scrolling should keep the
    # focused swatch visible. Use 10 colors and focus on the 9th.
    many = {f"color{i:02d}": f"#{i*25:02x}{i*10:02x}{i*5:02x}" for i in range(10)}
    f = Frame(30, 12)
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=many, filter_str="", sort_mode="name",
                          focused_idx=8)
    # Should not raise and should paint something (focused swatch must be visible)
    # Check that ◆ appears somewhere in the painted area
    marker_found = any(
        f.get(r, c).char == "◆"
        for r in range(10)
        for c in range(30)
    )
    assert marker_found


def test_swatch_browser_no_colors_no_crash():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors={}, filter_str="", sort_mode="name",
                          focused_idx=0)
    # Must not raise; paints "no results" or stays blank


def test_swatch_browser_row_col_offset():
    f = Frame(40, 16)
    render_swatch_browser(f, row=2, col=5, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # First swatch starts at row=2, col=5+1=6
    assert f.get(2, 6).bg == RGB(255, 0, 0)
    # row 0 untouched
    assert f.get(0, 6).char == " "
