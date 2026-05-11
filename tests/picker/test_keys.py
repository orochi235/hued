from src.picker.keys import Key, KeyEvent
from src.picker.term import parse_key


def test_keyevent_construction_char():
    e = KeyEvent(key=Key.CHAR, char="a", shift=False, ctrl=False)
    assert e.key is Key.CHAR
    assert e.char == "a"


def test_keyevent_special_no_char():
    e = KeyEvent(key=Key.ARROW_UP, char=None, shift=False, ctrl=False)
    assert e.key is Key.ARROW_UP
    assert e.char is None


def test_key_enum_has_required_members():
    expected = {"CHAR", "ARROW_UP", "ARROW_DOWN", "ARROW_LEFT", "ARROW_RIGHT",
                "ENTER", "TAB", "ESC", "BACKSPACE", "DELETE", "CTRL_C", "CTRL_L"}
    actual = {m.name for m in Key}
    assert expected <= actual


def test_parse_plain_char():
    e = parse_key(b"a")
    assert e.key is Key.CHAR and e.char == "a" and not e.shift and not e.ctrl


def test_parse_uppercase_char():
    e = parse_key(b"A")
    assert e.key is Key.CHAR and e.char == "A"


def test_parse_ctrl_c():
    assert parse_key(b"\x03").key is Key.CTRL_C


def test_parse_ctrl_l():
    assert parse_key(b"\x0c").key is Key.CTRL_L


def test_parse_enter_cr():
    assert parse_key(b"\r").key is Key.ENTER


def test_parse_enter_lf():
    assert parse_key(b"\n").key is Key.ENTER


def test_parse_tab():
    assert parse_key(b"\t").key is Key.TAB


def test_parse_backspace_del():
    assert parse_key(b"\x7f").key is Key.BACKSPACE


def test_parse_lone_esc():
    assert parse_key(b"\x1b").key is Key.ESC


def test_parse_arrow_up():
    assert parse_key(b"\x1b[A").key is Key.ARROW_UP


def test_parse_arrow_down():
    assert parse_key(b"\x1b[B").key is Key.ARROW_DOWN


def test_parse_arrow_right():
    assert parse_key(b"\x1b[C").key is Key.ARROW_RIGHT


def test_parse_arrow_left():
    assert parse_key(b"\x1b[D").key is Key.ARROW_LEFT


def test_parse_shift_arrow_left():
    # CSI 1;2 D — modifier 2 = shift
    e = parse_key(b"\x1b[1;2D")
    assert e.key is Key.ARROW_LEFT and e.shift


def test_parse_unknown_csi_returns_unknown():
    assert parse_key(b"\x1b[99~").key is Key.UNKNOWN
