from src.picker.frame import Cell, Frame
from src.picker.colors import RGB


def test_cell_defaults_to_space_and_none():
    c = Cell()
    assert c.char == " "
    assert c.fg is None
    assert c.bg is None


def test_cell_is_frozen():
    c = Cell(char="x")
    import dataclasses
    try:
        c.char = "y"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("Cell should be frozen")


def test_frame_dimensions():
    f = Frame(width=20, height=5)
    assert f.width == 20
    assert f.height == 5


def test_frame_starts_empty():
    f = Frame(width=4, height=2)
    for r in range(2):
        for c in range(4):
            assert f.get(r, c) == Cell()


def test_put_cell_sets_char_and_colors():
    f = Frame(5, 2)
    f.put_cell(0, 1, "x", fg=RGB(255, 0, 0), bg=RGB(0, 0, 0))
    assert f.get(0, 1) == Cell("x", RGB(255, 0, 0), RGB(0, 0, 0))


def test_put_cell_out_of_bounds_is_silent():
    f = Frame(3, 3)
    f.put_cell(-1, 0, "x")
    f.put_cell(0, -1, "x")
    f.put_cell(3, 0, "x")
    f.put_cell(0, 3, "x")
    for r in range(3):
        for c in range(3):
            assert f.get(r, c) == Cell()


def test_put_str_fills_consecutive_cells():
    f = Frame(10, 2)
    f.put_str(0, 2, "hi", fg=RGB(128, 128, 128))
    assert f.get(0, 2) == Cell("h", RGB(128, 128, 128), None)
    assert f.get(0, 3) == Cell("i", RGB(128, 128, 128), None)
    assert f.get(0, 1) == Cell()
    assert f.get(0, 4) == Cell()


def test_put_str_clips_at_right_edge():
    f = Frame(5, 1)
    f.put_str(0, 3, "abcde")
    assert f.get(0, 3).char == "a"
    assert f.get(0, 4).char == "b"


def test_put_str_negative_col_clips_left():
    f = Frame(5, 1)
    f.put_str(0, -2, "abcde")
    assert f.get(0, 0).char == "c"
    assert f.get(0, 1).char == "d"
    assert f.get(0, 2).char == "e"


def test_fill_paints_rectangle():
    f = Frame(5, 4)
    f.fill(1, 1, w=3, h=2, char="#", bg=RGB(20, 20, 20))
    assert f.get(0, 0) == Cell()
    assert f.get(3, 4) == Cell()
    for r in range(1, 3):
        for c in range(1, 4):
            assert f.get(r, c) == Cell("#", None, RGB(20, 20, 20))


def test_fill_clips_to_frame_bounds():
    f = Frame(3, 3)
    f.fill(2, 2, w=5, h=5, char="*")
    assert f.get(2, 2).char == "*"


def test_fill_zero_size_is_noop():
    f = Frame(3, 3)
    f.fill(0, 0, w=0, h=0, char="x")
    assert f.get(0, 0) == Cell()


def test_render_empty_frame_has_cursor_per_row_and_resets():
    f = Frame(3, 2)
    out = f.render()
    assert "\x1b[1;1H" in out
    assert "\x1b[2;1H" in out
    assert out.endswith("\x1b[0m")


def test_render_default_cells_emit_only_spaces():
    f = Frame(3, 1)
    out = f.render()
    assert "\x1b[48;2;" not in out
    assert "\x1b[38;2;" not in out
    assert out.count(" ") == 3


def test_render_painted_cell_emits_truecolor_codes():
    f = Frame(2, 1)
    f.put_cell(0, 0, "X", fg=RGB(255, 0, 0), bg=RGB(0, 0, 255))
    out = f.render()
    assert "\x1b[38;2;255;0;0m" in out
    assert "\x1b[48;2;0;0;255m" in out
    assert "X" in out


def test_render_suppresses_repeated_color_within_row():
    f = Frame(3, 1)
    red = RGB(255, 0, 0)
    f.put_cell(0, 0, "a", fg=red)
    f.put_cell(0, 1, "b", fg=red)
    f.put_cell(0, 2, "c", fg=red)
    out = f.render()
    assert out.count("\x1b[38;2;255;0;0m") == 1


def test_render_resets_between_rows():
    f = Frame(2, 2)
    red = RGB(255, 0, 0)
    f.put_cell(0, 0, "a", fg=red)
    out = f.render()
    idx = out.index("\x1b[2;1H")
    second_row = out[idx:]
    assert "\x1b[0m" in out[:idx] or "\x1b[0m" in second_row[:20]


import io


def test_flush_writes_and_flushes():
    f = Frame(2, 1)
    f.put_cell(0, 0, "X", fg=RGB(1, 2, 3))
    buf = io.StringIO()
    f.flush(buf)
    text = buf.getvalue()
    assert text == f.render()
    assert "X" in text


def test_box_draws_corners_and_edges():
    f = Frame(6, 4)
    f.box(0, 0, w=6, h=4)
    assert f.get(0, 0).char == "┌"
    assert f.get(0, 5).char == "┐"
    assert f.get(3, 0).char == "└"
    assert f.get(3, 5).char == "┘"
    for c in range(1, 5):
        assert f.get(0, c).char == "─"
        assert f.get(3, c).char == "─"
    for r in range(1, 3):
        assert f.get(r, 0).char == "│"
        assert f.get(r, 5).char == "│"


def test_box_does_not_overwrite_interior():
    f = Frame(5, 3)
    f.put_cell(1, 2, "X", fg=RGB(10, 20, 30))
    f.box(0, 0, 5, 3)
    assert f.get(1, 2) == Cell("X", RGB(10, 20, 30), None)


def test_box_fg_propagates_to_border():
    f = Frame(4, 3)
    f.box(0, 0, 4, 3, fg=RGB(100, 100, 100))
    assert f.get(0, 0).fg == RGB(100, 100, 100)
    assert f.get(2, 0).fg == RGB(100, 100, 100)


def test_box_too_small_does_nothing_or_clips_gracefully():
    f = Frame(5, 5)
    f.box(0, 0, 1, 1)
