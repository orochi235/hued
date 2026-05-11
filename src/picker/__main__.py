"""src.picker package entry point.

Without --app:  run the Phase 2 smoke test (Frame rendering demo).
With    --app:  run the interactive color picker (Phase 4 app).

Usage:
  python3 -m src.picker          # smoke test
  python3 -m src.picker --app    # full interactive picker
  python3 -m src.picker --app --bg '#1a0a0a' --live
"""
import sys


def _smoke_main() -> int:
    """Phase 2 smoke test: renders a bordered frame with swatches."""
    from src.picker import term as t
    from src.picker.colors import RGB, hex_to_rgb
    from src.picker.frame import Frame
    from src.picker.names import NAMED_COLORS

    SWATCH_HEXES = [
        "#ff5555", "#ffaa55", "#ffff55", "#55ff55",
        "#55ffff", "#5555ff", "#aa55ff", "#ff55aa",
    ]

    first_name = next(iter(NAMED_COLORS))
    first_hex = NAMED_COLORS[first_name]

    def build_frame(cols: int, rows: int) -> Frame:
        f = Frame(cols, rows)
        f.box(0, 0, cols, rows, fg=RGB(128, 128, 128))
        for i, hex_v in enumerate(SWATCH_HEXES):
            rgb = hex_to_rgb(hex_v)
            f.fill(1, 1 + i * 8, w=8, h=1, char=" ", bg=rgb)
        f.put_str(3, 2, f"terminal bg: {first_name} ({first_hex})")
        f.put_str(5, 2, "press any key to exit (try arrow keys, shift+arrow, ctrl-c)")
        return f

    sys.stdout.write(t.enter_alt_screen())
    sys.stdout.write(t.hide_cursor())
    sys.stdout.write(t.clear_screen())
    sys.stdout.flush()
    t.osc_bg(first_hex)

    def on_resize(cols: int, rows: int) -> None:
        sys.stdout.write(t.clear_screen())
        build_frame(cols, rows).flush()

    t.install_resize_handler(on_resize)

    try:
        cols, rows = t.get_size()
        build_frame(cols, rows).flush()
        with t.raw_mode():
            event = t.read_key()
    finally:
        t.uninstall_resize_handler()
        t.osc_reset_bg()
        t.osc_reset_fg()
        sys.stdout.write(t.show_cursor())
        sys.stdout.write(t.exit_alt_screen())
        sys.stdout.flush()

    print(f"got: key={event.key.name} char={event.char!r} "
          f"shift={event.shift} ctrl={event.ctrl}")
    return 0


def main() -> int:
    if "--app" in sys.argv:
        # Strip --app from argv before passing to app.main()
        argv = [a for a in sys.argv[1:] if a != "--app"]
        from src.picker.app import main as app_main
        return app_main(argv)
    return _smoke_main()


if __name__ == "__main__":
    raise SystemExit(main())
