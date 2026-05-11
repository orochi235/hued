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
