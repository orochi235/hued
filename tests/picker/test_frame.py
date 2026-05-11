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
