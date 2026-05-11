from src.picker.term import (
    ansi_truecolor_bg, ansi_truecolor_fg, ansi_reset,
    cursor_to, hide_cursor, show_cursor,
    enter_alt_screen, exit_alt_screen, clear_screen,
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
