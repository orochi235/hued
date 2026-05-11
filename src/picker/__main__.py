"""picker — interactive terminal color picker.

Run:
  python3 -m picker [--bg <hex>] [--fg <hex>] [--live] [--output <file>]
  python3 -m picker --help

The --smoke flag invokes the Phase 2 frame smoke test (development only).
"""
import sys


def main() -> int:
    if "--smoke" in sys.argv:
        # Phase 2 smoke test path — development only, not invoked by the shim
        from src.picker import term as t
        from src.picker.colors import hex_to_rgb
        from src.picker.frame import Frame
        from src.picker.names import NAMED_COLORS

        first_name = next(iter(NAMED_COLORS))
        first_hex = NAMED_COLORS[first_name]

        sys.stdout.write(t.enter_alt_screen())
        sys.stdout.write(t.hide_cursor())
        sys.stdout.write(t.clear_screen())
        sys.stdout.flush()
        t.osc_bg(first_hex)

        def on_resize(cols: int, rows: int) -> None:
            sys.stdout.write(t.clear_screen())
            _smoke_render(cols, rows, first_name, first_hex)

        t.install_resize_handler(on_resize)

        try:
            cols, rows = t.get_size()
            _smoke_render(cols, rows, first_name, first_hex)
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

    # Default: launch the interactive picker (Phase 4 app)
    from src.picker.app import main as app_main
    return app_main()


def _smoke_render(cols: int, rows: int, first_name: str, first_hex: str) -> None:
    from src.picker.colors import hex_to_rgb
    from src.picker.colors import RGB
    from src.picker.frame import Frame
    from src.picker import term as t

    SWATCH_HEXES = ["#ff5555", "#ffaa55", "#ffff55", "#55ff55",
                    "#55ffff", "#5555ff", "#aa55ff", "#ff55aa"]
    f = Frame(cols, rows)
    f.box(0, 0, cols, rows, fg=RGB(128, 128, 128))
    for i, hex_v in enumerate(SWATCH_HEXES):
        rgb = hex_to_rgb(hex_v)
        f.fill(1, 1 + i * 8, w=8, h=1, char=" ", bg=rgb)
    f.put_str(3, 2, f"terminal bg: {first_name} ({first_hex})")
    f.put_str(5, 2, "press any key to exit (try arrow keys, shift+arrow, ctrl-c)")
    f.flush()


if __name__ == "__main__":
    raise SystemExit(main())
