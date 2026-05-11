from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.slider import render_slider


def _frame(w=40, h=5):
    return Frame(w, h)


def test_slider_paints_label_at_col0():
    f = _frame()
    render_slider(f, row=0, col=0, w=38, h=3, label="R", value=128, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Label "R " starts at col 0, row 0
    assert f.get(0, 0).char == "R"
    assert f.get(0, 1).char == " "


def test_slider_paints_value_right_aligned():
    f = _frame()
    # value=255 -> " 255" in the last VALUE_W=4 columns starting at col LABEL_W+track_w
    render_slider(f, row=0, col=0, w=38, h=3, label="R", value=255, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    LABEL_W, VALUE_W = 2, 4
    track_w = max(4, 38 - LABEL_W - VALUE_W)
    value_col = LABEL_W + track_w
    text_in_frame = "".join(f.get(0, value_col + i).char for i in range(VALUE_W))
    assert text_in_frame == " 255"


def test_slider_track_cells_have_bg_color():
    f = _frame()
    render_slider(f, row=0, col=0, w=38, h=3, label="G", value=0, max=255,
                  get_color=lambda v: RGB(0, v, 0))
    # Track starts at col LABEL_W=2; the first cell is for value 0 -> RGB(0,0,0)
    cell = f.get(0, 2)
    assert cell.bg == RGB(0, 0, 0)


def test_slider_marker_at_correct_position():
    f = _frame()
    # value=0 -> marker at leftmost track position (col LABEL_W)
    render_slider(f, row=0, col=0, w=38, h=3, label="B", value=0, max=255,
                  focused=True, get_color=lambda v: RGB(0, 0, v))
    assert f.get(0, 2).char == "◆"


def test_slider_no_marker_when_not_focused():
    f = _frame()
    render_slider(f, row=0, col=0, w=38, h=3, label="B", value=0, max=255,
                  focused=False, get_color=lambda v: RGB(0, 0, v))
    # No ◆ in track row
    LABEL_W = 2
    assert f.get(0, LABEL_W).char != "◆"


def test_slider_shadow_row1_has_shadow_cell():
    f = _frame()
    LABEL_W, VALUE_W = 2, 4
    w = 38
    track_w = max(4, w - LABEL_W - VALUE_W)
    render_slider(f, row=0, col=0, w=w, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Row 1: shadow cell appears at col LABEL_W + track_w
    shadow_cell = f.get(1, LABEL_W + track_w)
    assert shadow_cell.bg == RGB(26, 26, 26)


def test_slider_shadow_row2_has_shadow_strip():
    f = _frame()
    LABEL_W, VALUE_W = 2, 4
    w = 38
    track_w = max(4, w - LABEL_W - VALUE_W)
    render_slider(f, row=0, col=0, w=w, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Row 2 shadow starts at col LABEL_W+1 and is track_w wide
    for c in range(track_w):
        assert f.get(2, LABEL_W + 1 + c).bg == RGB(26, 26, 26)


def test_slider_col_offset_respected():
    f = _frame(w=50)
    render_slider(f, row=1, col=5, w=38, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Label starts at col 5, not col 0
    assert f.get(1, 5).char == "R"
    assert f.get(1, 0).char == " "  # untouched


def test_slider_fallback_no_get_color():
    f = _frame()
    # When get_color is None, slider paints 1 row: filled blocks + empty blocks
    render_slider(f, row=0, col=0, w=38, h=1, label="R", value=128, max=255,
                  get_color=None)
    # Row 0 should contain at least one '█' and one '░'
    row_chars = [f.get(0, c).char for c in range(38)]
    assert "█" in row_chars
    assert "░" in row_chars


def test_slider_out_of_bounds_rows_dont_crash():
    # Frame has only 2 rows but slider requests 3; rows 2+ are silently clipped
    f = Frame(40, 2)
    render_slider(f, row=0, col=0, w=38, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Row 0 should still be painted
    assert f.get(0, 0).char == "R"
