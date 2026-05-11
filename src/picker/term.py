from __future__ import annotations
import sys
import os
import termios
import tty
import select
import shutil
from contextlib import contextmanager
from typing import IO, Iterator
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


def osc_bg(hex_value: str, stream: IO[str] = sys.stdout) -> None:
    """Emit OSC 11: set terminal background. hex_value e.g. '#1a0a0a'."""
    h = hex_value.lstrip("#")
    stream.write(f"\x1b]11;rgb:{h[0:2]}/{h[2:4]}/{h[4:6]}\x07")
    stream.flush()


def osc_fg(hex_value: str, stream: IO[str] = sys.stdout) -> None:
    h = hex_value.lstrip("#")
    stream.write(f"\x1b]10;rgb:{h[0:2]}/{h[2:4]}/{h[4:6]}\x07")
    stream.flush()


def osc_reset_bg(stream: IO[str] = sys.stdout) -> None:
    stream.write("\x1b]111;\x07")
    stream.flush()


def osc_reset_fg(stream: IO[str] = sys.stdout) -> None:
    stream.write("\x1b]110;\x07")
    stream.flush()


def ansi_truecolor_bg(r: int, g: int, b: int) -> str:
    return f"\x1b[48;2;{r};{g};{b}m"


def ansi_truecolor_fg(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"


def ansi_reset() -> str:
    return "\x1b[0m"


def cursor_to(row: int, col: int) -> str:
    """1-indexed row/col."""
    return f"\x1b[{row};{col}H"


def hide_cursor() -> str:
    return "\x1b[?25l"


def show_cursor() -> str:
    return "\x1b[?25h"


def enter_alt_screen() -> str:
    return "\x1b[?1049h"


def exit_alt_screen() -> str:
    return "\x1b[?1049l"


def clear_screen() -> str:
    return "\x1b[2J"


@contextmanager
def raw_mode(fd: int = 0) -> Iterator[None]:
    """Put fd (default stdin) into cbreak mode for the duration of the with-block."""
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_key(fd: int = 0, timeout: float = 0.05) -> "KeyEvent":
    """Read one key from fd (which must be in raw/cbreak mode).

    Blocks for at least one byte, then drains any continuation bytes that
    arrive within `timeout` seconds — this is how multi-byte escape
    sequences (arrow keys, modified keys) get bundled into a single event.
    """
    first = os.read(fd, 1)
    if not first:
        return KeyEvent(Key.UNKNOWN, None, False, False)
    buf = bytearray(first)
    # Drain follow-up bytes (escape sequences arrive together but not atomically)
    while True:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            break
        more = os.read(fd, 16)
        if not more:
            break
        buf.extend(more)
    return parse_key(bytes(buf))


def get_size() -> tuple[int, int]:
    """Return (columns, rows) for the controlling terminal."""
    s = shutil.get_terminal_size((80, 24))
    return s.columns, s.lines
