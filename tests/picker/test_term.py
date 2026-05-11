import os
import signal
import time
from src.picker.term import (
    ansi_truecolor_bg, ansi_truecolor_fg, ansi_reset,
    cursor_to, hide_cursor, show_cursor,
    enter_alt_screen, exit_alt_screen, clear_screen,
    get_size,
    install_resize_handler, uninstall_resize_handler,
)


def test_ansi_truecolor_bg():
    assert ansi_truecolor_bg(255, 0, 128) == "\x1b[48;2;255;0;128m"


def test_ansi_truecolor_fg():
    assert ansi_truecolor_fg(1, 2, 3) == "\x1b[38;2;1;2;3m"


def test_ansi_reset():
    assert ansi_reset() == "\x1b[0m"


def test_cursor_to():
    assert cursor_to(5, 10) == "\x1b[5;10H"


def test_screen_helpers():
    assert hide_cursor() == "\x1b[?25l"
    assert show_cursor() == "\x1b[?25h"
    assert enter_alt_screen() == "\x1b[?1049h"
    assert exit_alt_screen() == "\x1b[?1049l"
    assert clear_screen() == "\x1b[2J"


def test_get_size_returns_positive_pair():
    cols, rows = get_size()
    assert cols >= 1 and rows >= 1


def test_resize_handler_fires_on_sigwinch():
    fired = []

    def on_resize(cols: int, rows: int) -> None:
        fired.append((cols, rows))

    install_resize_handler(on_resize)
    try:
        os.kill(os.getpid(), signal.SIGWINCH)
        time.sleep(0.05)
        assert len(fired) == 1
        cols, rows = fired[0]
        assert cols >= 1 and rows >= 1
    finally:
        uninstall_resize_handler()


def test_uninstall_resize_handler_restores_default():
    install_resize_handler(lambda c, r: None)
    uninstall_resize_handler()
