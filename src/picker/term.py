from __future__ import annotations
from src.picker.keys import Key, KeyEvent


_ARROW = {"A": Key.ARROW_UP, "B": Key.ARROW_DOWN,
          "C": Key.ARROW_RIGHT, "D": Key.ARROW_LEFT}


def parse_key(buf: bytes) -> KeyEvent:
    """Translate a single key's worth of bytes into a KeyEvent.

    Buffer contents:
      - single printable byte         -> CHAR
      - 0x01-0x1a (ctrl-A..ctrl-Z)    -> CTRL_* (specific ones recognized)
      - 0x09 tab, 0x0a/0x0d enter, 0x7f backspace
      - 0x1b alone                    -> ESC
      - 0x1b [ <letter>               -> arrow keys
      - 0x1b [ 1 ; <mod> <letter>     -> shift/ctrl-modified arrows
    Anything else returns Key.UNKNOWN.
    """
    if not buf:
        return KeyEvent(Key.UNKNOWN, None, False, False)

    # Control bytes
    if len(buf) == 1:
        b = buf[0]
        if b == 0x03:
            return KeyEvent(Key.CTRL_C, None, False, True)
        if b == 0x0c:
            return KeyEvent(Key.CTRL_L, None, False, True)
        if b == 0x09:
            return KeyEvent(Key.TAB, None, False, False)
        if b in (0x0a, 0x0d):
            return KeyEvent(Key.ENTER, None, False, False)
        if b == 0x7f:
            return KeyEvent(Key.BACKSPACE, None, False, False)
        if b == 0x1b:
            return KeyEvent(Key.ESC, None, False, False)
        if 0x20 <= b < 0x7f:
            return KeyEvent(Key.CHAR, chr(b), False, False)
        return KeyEvent(Key.UNKNOWN, None, False, False)

    # CSI sequences: ESC [ ...
    if buf[:2] == b"\x1b[":
        body = buf[2:]
        # Plain arrow: <letter>
        if len(body) == 1 and 65 <= body[0] <= 68:  # A..D
            return KeyEvent(_ARROW[chr(body[0])], None, False, False)
        # Modified arrow: 1 ; <mod> <letter>
        if len(body) >= 4 and body[0:2] == b"1;" and 65 <= body[-1] <= 68:
            try:
                mod = int(body[2:-1])
            except ValueError:
                return KeyEvent(Key.UNKNOWN, None, False, False)
            shift = bool((mod - 1) & 1)
            ctrl = bool((mod - 1) & 4)
            return KeyEvent(_ARROW[chr(body[-1])], None, shift, ctrl)
        return KeyEvent(Key.UNKNOWN, None, False, False)

    return KeyEvent(Key.UNKNOWN, None, False, False)
