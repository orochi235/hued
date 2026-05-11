from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.settings import render_settings


def _frame(w=30, h=8):
    return Frame(w, h)


def test_settings_active_model_painted_at_row1():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#ff0000", nearest_name="red")
    # "RGB" should appear on row 1 starting at col 1 (1-char padding)
    row1 = "".join(f.get(1, c).char for c in range(30))
    assert "RGB" in row1


def test_settings_all_models_appear():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="hsl", step="fg", live=False,
                    current_hex="#00ff00", nearest_name="lime")
    row1 = "".join(f.get(1, c).char for c in range(30))
    for model_text in ("RGB", "HSL", "OKLCH", "LAB"):
        assert model_text in row1, f"missing {model_text!r} in row1: {row1!r}"


def test_settings_active_model_is_cyan():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="oklch", step="bg", live=True,
                    current_hex="#0000ff", nearest_name="blue")
    # The 'O' of OKLCH should be cyan
    row1 = "".join(f.get(1, c).char for c in range(30))
    idx = row1.index("O")
    assert f.get(1, idx).fg == RGB(0, 255, 255)


def test_settings_active_step_is_cyan():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="fg", live=False,
                    current_hex="#ffffff", nearest_name="white")
    row2 = "".join(f.get(2, c).char for c in range(30))
    idx = row2.index("f")  # 'fg' starts with 'f'
    # The 'f' of 'fg' should be cyan
    assert f.get(2, idx).fg == RGB(0, 255, 255)


def test_settings_live_indicator_checked():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#ff0000", nearest_name="red")
    row3 = "".join(f.get(3, c).char for c in range(30))
    assert "✓" in row3


def test_settings_live_indicator_unchecked():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=False,
                    current_hex="#ff0000", nearest_name="red")
    row3 = "".join(f.get(3, c).char for c in range(30))
    assert "✓" not in row3
    assert "[" in row3 and "]" in row3


def test_settings_hex_appears_on_row4():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#aabbcc", nearest_name="something")
    row4 = "".join(f.get(4, c).char for c in range(30))
    assert "#aabbcc" in row4


def test_settings_nearest_name_appears_on_row4():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#aabbcc", nearest_name="powderblue")
    row4 = "".join(f.get(4, c).char for c in range(30))
    assert "powderblue" in row4


def test_settings_col_offset():
    f = Frame(40, 8)
    render_settings(f, row=0, col=5, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#ff0000", nearest_name="red")
    # col 0-4 untouched
    assert f.get(1, 0).char == " "
    # The model label begins at col 6 (col=5 + 1 padding)
    row1 = "".join(f.get(1, c).char for c in range(40))
    assert "RGB" in row1
