"""Phase 1 smoke test for src.picker.

Run: python3 -m src.picker

What it does:
  1. Enters the alternate screen, hides the cursor.
  2. Draws a row of 8 truecolor swatches across the top.
  3. Sets the terminal bg via OSC to the first named color from NAMED_COLORS.
  4. Prints a help line.
  5. Waits for a single keypress; echoes which key was pressed.
  6. Resets terminal bg, exits alt screen, restores cursor.
"""
import sys
from src.picker import term as t
from src.picker.colors import rgb_to_hex, hex_to_rgb
from src.picker.names import NAMED_COLORS


SWATCH_HEXES = ["#ff5555", "#ffaa55", "#ffff55", "#55ff55",
                "#55ffff", "#5555ff", "#aa55ff", "#ff55aa"]


def draw(first_name: str, first_hex: str) -> None:
    out = sys.stdout
    out.write(t.cursor_to(1, 1))
    for hex_v in SWATCH_HEXES:
        rgb = hex_to_rgb(hex_v)
        out.write(t.ansi_truecolor_bg(rgb.r, rgb.g, rgb.b))
        out.write("        ")
    out.write(t.ansi_reset())
    out.write(t.cursor_to(3, 1))
    out.write(f"terminal bg set to {first_name} ({first_hex})")
    out.write(t.cursor_to(5, 1))
    out.write("press any key to exit (try arrow keys, shift+arrow, ctrl-c)")
    out.flush()


def main() -> int:
    first_name = next(iter(NAMED_COLORS))
    first_hex = NAMED_COLORS[first_name]

    sys.stdout.write(t.enter_alt_screen())
    sys.stdout.write(t.hide_cursor())
    sys.stdout.write(t.clear_screen())
    sys.stdout.flush()
    t.osc_bg(first_hex)

    try:
        draw(first_name, first_hex)
        with t.raw_mode():
            event = t.read_key()
    finally:
        t.osc_reset_bg()
        t.osc_reset_fg()
        sys.stdout.write(t.show_cursor())
        sys.stdout.write(t.exit_alt_screen())
        sys.stdout.flush()

    print(f"got: key={event.key.name} char={event.char!r} "
          f"shift={event.shift} ctrl={event.ctrl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
