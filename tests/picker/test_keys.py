from src.picker.keys import Key, KeyEvent


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
