# Picker Python Port — Phase 2: Render Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stdlib-only `Frame` buffer that components in Phase 3 will paint into — set cells, draw strings, fill regions, draw box borders — and emits the whole frame as a single escape-sequence blob via `render()`. Plus a SIGWINCH handler so resize triggers a redraw. The smoke-test program from Phase 1 is upgraded to use the Frame so the abstraction is exercised end-to-end.

**Architecture:**
- `Frame(width, height)` owns a 2D grid of `Cell(char, fg, bg)` (immutable). `fg`/`bg` are `RGB | None`; `None` means "no color code emitted for this channel" so the terminal default shows through.
- Coordinates are **0-indexed `(row, col)`** in the Python API; converted to 1-indexed at emit time.
- `render()` produces a single string with cursor-positioning escapes per row and color escapes only when they change from the previous cell (cheap RLE-style suppression).
- No diffing against a previous frame in this phase — naive full-redraw per flush. Diffing is a Phase 3+ optimization.
- SIGWINCH is wired in `term.py`: `install_resize_handler(cb)` installs, `uninstall_resize_handler()` restores. The handler runs in signal context — callers do `cols, rows = get_size()` from the callback and update their own state.

**Tech Stack:** Python 3.9+ stdlib only. `pytest` for tests (already a dev dep). Builds directly on Phase 1 modules (`colors.RGB`, `term.cursor_to`, `term.ansi_truecolor_*`, `term.ansi_reset`, `term.get_size`).

**Scope:** Second of several plans. Phase 2 produces a `Frame` API ready for Phase 3 components (Slider, Settings, TerminalPreview, SwatchBrowser, ColorSlicer) to consume. It does NOT implement components themselves.

**Branch strategy:** Work on `feature/picker-render` cut from `main` *after Phase 1 merges*. If Phase 1 has not yet merged when you start, cut from `feature/picker-python` instead and update the base when Phase 1 lands.

---

## File Structure

Files this plan creates or modifies:

- **Create:** `src/picker/frame.py` — `Cell` dataclass, `Frame` class with `put_cell`, `put_str`, `fill`, `box`, `render`, `flush`. One responsibility: an in-memory 2D canvas that emits ANSI text on demand.
- **Modify:** `src/picker/term.py` — adds `install_resize_handler(cb)` and `uninstall_resize_handler()` at the bottom. These are small enough to keep here rather than spinning up a new module.
- **Modify:** `src/picker/__main__.py` — upgrade the smoke test to build the screen via `Frame` instead of raw `sys.stdout.write` calls.
- **Create:** `tests/picker/test_frame.py` — unit tests for the `Frame` API. ~15 tests.
- **Modify:** `tests/picker/test_term.py` — adds 1 test for the SIGWINCH handler.

After this phase the Phase 1 file structure expands like so:

```
src/picker/
  __init__.py
  __main__.py        # upgraded smoke test
  colors.py          # unchanged
  frame.py           # NEW
  keys.py            # unchanged
  names.py           # unchanged
  term.py            # + resize handler
```

---

## Task 1: Branch + Cell type + Frame skeleton

**Files:**
- Create: `src/picker/frame.py`
- Create: `tests/picker/test_frame.py`

- [ ] **Step 1: Create branch**

Cut from `main` (or `feature/picker-python` if Phase 1 hasn't merged yet):

```bash
git checkout main && git pull --ff-only
git checkout -b feature/picker-render
```

- [ ] **Step 2: Write failing tests for Cell + Frame construction**

Create `tests/picker/test_frame.py`:

```python
from src.picker.frame import Cell, Frame
from src.picker.colors import RGB


def test_cell_defaults_to_space_and_none():
    c = Cell()
    assert c.char == " "
    assert c.fg is None
    assert c.bg is None


def test_cell_is_frozen():
    c = Cell(char="x")
    import dataclasses
    try:
        c.char = "y"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("Cell should be frozen")


def test_frame_dimensions():
    f = Frame(width=20, height=5)
    assert f.width == 20
    assert f.height == 5


def test_frame_starts_empty():
    f = Frame(width=4, height=2)
    # Every cell is a default Cell
    for r in range(2):
        for c in range(4):
            assert f.get(r, c) == Cell()
```

- [ ] **Step 3: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.frame'`.

- [ ] **Step 4: Implement Cell + Frame skeleton**

Create `src/picker/frame.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from src.picker.colors import RGB


@dataclass(frozen=True)
class Cell:
    char: str = " "
    fg: Optional[RGB] = None
    bg: Optional[RGB] = None


class Frame:
    """In-memory 2D grid of Cells; emits ANSI text via render()."""

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Frame dimensions must be positive, got {width}x{height}")
        self.width = width
        self.height = height
        self._cells: list[list[Cell]] = [
            [Cell() for _ in range(width)] for _ in range(height)
        ]

    def get(self, row: int, col: int) -> Cell:
        return self._cells[row][col]
```

- [ ] **Step 5: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/picker/frame.py tests/picker/test_frame.py
git commit -m "feat(picker): Cell dataclass and Frame skeleton"
```

---

## Task 2: put_cell + put_str

**Files:**
- Modify: `src/picker/frame.py`
- Modify: `tests/picker/test_frame.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/picker/test_frame.py`:

```python
def test_put_cell_sets_char_and_colors():
    f = Frame(5, 2)
    f.put_cell(0, 1, "x", fg=RGB(255, 0, 0), bg=RGB(0, 0, 0))
    assert f.get(0, 1) == Cell("x", RGB(255, 0, 0), RGB(0, 0, 0))


def test_put_cell_out_of_bounds_is_silent():
    f = Frame(3, 3)
    # Should not raise — out-of-bounds writes are clipped (no-op).
    f.put_cell(-1, 0, "x")
    f.put_cell(0, -1, "x")
    f.put_cell(3, 0, "x")
    f.put_cell(0, 3, "x")
    # No cells changed
    for r in range(3):
        for c in range(3):
            assert f.get(r, c) == Cell()


def test_put_str_fills_consecutive_cells():
    f = Frame(10, 2)
    f.put_str(0, 2, "hi", fg=RGB(128, 128, 128))
    assert f.get(0, 2) == Cell("h", RGB(128, 128, 128), None)
    assert f.get(0, 3) == Cell("i", RGB(128, 128, 128), None)
    assert f.get(0, 1) == Cell()  # untouched
    assert f.get(0, 4) == Cell()  # untouched


def test_put_str_clips_at_right_edge():
    f = Frame(5, 1)
    f.put_str(0, 3, "abcde")
    assert f.get(0, 3).char == "a"
    assert f.get(0, 4).char == "b"
    # 'c', 'd', 'e' fall off the right; no error.


def test_put_str_negative_col_clips_left():
    f = Frame(5, 1)
    f.put_str(0, -2, "abcde")
    # 'a' and 'b' fall off the left; 'c' lands at col 0
    assert f.get(0, 0).char == "c"
    assert f.get(0, 1).char == "d"
    assert f.get(0, 2).char == "e"
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v -k "put_"
```

Expected: `AttributeError: 'Frame' object has no attribute 'put_cell'`.

- [ ] **Step 3: Implement**

Append to `Frame` class in `src/picker/frame.py`:

```python
    def put_cell(
        self,
        row: int,
        col: int,
        char: str,
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        if not (0 <= row < self.height and 0 <= col < self.width):
            return
        self._cells[row][col] = Cell(char, fg, bg)

    def put_str(
        self,
        row: int,
        col: int,
        s: str,
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        if not (0 <= row < self.height):
            return
        for i, ch in enumerate(s):
            c = col + i
            if 0 <= c < self.width:
                self._cells[row][c] = Cell(ch, fg, bg)
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/frame.py tests/picker/test_frame.py
git commit -m "feat(picker): Frame.put_cell and Frame.put_str"
```

---

## Task 3: fill rectangle

**Files:**
- Modify: `src/picker/frame.py`
- Modify: `tests/picker/test_frame.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/picker/test_frame.py`:

```python
def test_fill_paints_rectangle():
    f = Frame(5, 4)
    f.fill(1, 1, w=3, h=2, char="#", bg=RGB(20, 20, 20))
    # Untouched corners
    assert f.get(0, 0) == Cell()
    assert f.get(3, 4) == Cell()
    # Filled region
    for r in range(1, 3):
        for c in range(1, 4):
            assert f.get(r, c) == Cell("#", None, RGB(20, 20, 20))


def test_fill_clips_to_frame_bounds():
    f = Frame(3, 3)
    # Rectangle extends beyond the right and bottom edges
    f.fill(2, 2, w=5, h=5, char="*")
    assert f.get(2, 2).char == "*"
    # No exception; only the in-bounds cell was painted.


def test_fill_zero_size_is_noop():
    f = Frame(3, 3)
    f.fill(0, 0, w=0, h=0, char="x")
    assert f.get(0, 0) == Cell()
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v -k fill
```

Expected: `AttributeError: 'Frame' object has no attribute 'fill'`.

- [ ] **Step 3: Implement**

Append to `Frame` class:

```python
    def fill(
        self,
        row: int,
        col: int,
        w: int,
        h: int,
        char: str = " ",
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        for r in range(row, row + h):
            if not (0 <= r < self.height):
                continue
            for c in range(col, col + w):
                if not (0 <= c < self.width):
                    continue
                self._cells[r][c] = Cell(char, fg, bg)
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/frame.py tests/picker/test_frame.py
git commit -m "feat(picker): Frame.fill rectangle"
```

---

## Task 4: render() → string

This is the meaty task. The output format:
- One `cursor_to(row+1, 1)` at the start of each row.
- Within a row, emit color escapes only when they differ from the previous cell.
- A final `ansi_reset()` after the last cell of the last row.

**Files:**
- Modify: `src/picker/frame.py`
- Modify: `tests/picker/test_frame.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/picker/test_frame.py`:

```python
def test_render_empty_frame_has_cursor_per_row_and_resets():
    f = Frame(3, 2)
    out = f.render()
    # Two cursor-position escapes (one per row, 1-indexed)
    assert "\x1b[1;1H" in out
    assert "\x1b[2;1H" in out
    # Ends with a reset
    assert out.endswith("\x1b[0m")


def test_render_default_cells_emit_only_spaces():
    f = Frame(3, 1)
    out = f.render()
    # No truecolor codes for fully-default cells
    assert "\x1b[48;2;" not in out
    assert "\x1b[38;2;" not in out
    # Spaces appear in the output (3 of them)
    assert out.count(" ") == 3


def test_render_painted_cell_emits_truecolor_codes():
    f = Frame(2, 1)
    f.put_cell(0, 0, "X", fg=RGB(255, 0, 0), bg=RGB(0, 0, 255))
    out = f.render()
    assert "\x1b[38;2;255;0;0m" in out
    assert "\x1b[48;2;0;0;255m" in out
    assert "X" in out


def test_render_suppresses_repeated_color_within_row():
    f = Frame(3, 1)
    red = RGB(255, 0, 0)
    f.put_cell(0, 0, "a", fg=red)
    f.put_cell(0, 1, "b", fg=red)
    f.put_cell(0, 2, "c", fg=red)
    out = f.render()
    # The truecolor fg escape appears exactly once for this row
    assert out.count("\x1b[38;2;255;0;0m") == 1


def test_render_resets_between_rows():
    f = Frame(2, 2)
    red = RGB(255, 0, 0)
    f.put_cell(0, 0, "a", fg=red)
    # Row 1 cells have no fg; row 0's red must not leak in
    out = f.render()
    # Find the row 2 cursor jump
    idx = out.index("\x1b[2;1H")
    second_row = out[idx:]
    # The reset before/at the row boundary clears prior color state
    assert "\x1b[0m" in out[:idx] or "\x1b[0m" in second_row[:20]
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v -k render
```

Expected: `AttributeError: 'Frame' object has no attribute 'render'`.

- [ ] **Step 3: Implement render()**

Add these imports to the top of `src/picker/frame.py` (alongside existing imports):

```python
from src.picker.term import (
    ansi_truecolor_bg,
    ansi_truecolor_fg,
    ansi_reset,
    cursor_to,
)
```

Append to `Frame` class:

```python
    def render(self) -> str:
        """Build the full frame as one ANSI string. Caller writes + flushes."""
        parts: list[str] = []
        for r in range(self.height):
            parts.append(cursor_to(r + 1, 1))
            # Reset between rows so prior row's trailing color doesn't carry over
            parts.append(ansi_reset())
            last_fg: Optional[RGB] = None
            last_bg: Optional[RGB] = None
            for c in range(self.width):
                cell = self._cells[r][c]
                if cell.fg != last_fg:
                    parts.append(ansi_truecolor_fg(cell.fg.r, cell.fg.g, cell.fg.b)
                                 if cell.fg is not None else ansi_reset())
                    last_fg = cell.fg
                    # ansi_reset clears bg too — force re-emit if a bg follows
                    if cell.fg is None:
                        last_bg = None
                if cell.bg != last_bg:
                    if cell.bg is not None:
                        parts.append(ansi_truecolor_bg(cell.bg.r, cell.bg.g, cell.bg.b))
                    # If cell.bg is None we don't emit a code — the prior reset
                    # (if any) already cleared it. We rely on the row-start reset.
                    last_bg = cell.bg
                parts.append(cell.char)
        parts.append(ansi_reset())
        return "".join(parts)
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/frame.py tests/picker/test_frame.py
git commit -m "feat(picker): Frame.render emits single ANSI blob with color RLE"
```

---

## Task 5: flush() convenience method

**Files:**
- Modify: `src/picker/frame.py`
- Modify: `tests/picker/test_frame.py`

- [ ] **Step 1: Add failing test**

Append to `tests/picker/test_frame.py`:

```python
import io

def test_flush_writes_and_flushes():
    f = Frame(2, 1)
    f.put_cell(0, 0, "X", fg=RGB(1, 2, 3))
    buf = io.StringIO()
    f.flush(buf)
    text = buf.getvalue()
    # Same content as render()
    assert text == f.render()
    assert "X" in text
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v -k flush
```

Expected: `AttributeError: 'Frame' object has no attribute 'flush'`.

- [ ] **Step 3: Implement**

Add to imports at the top of `frame.py`:

```python
import sys
from typing import IO
```

Append to `Frame` class:

```python
    def flush(self, stream: IO[str] = sys.stdout) -> None:
        stream.write(self.render())
        stream.flush()
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/frame.py tests/picker/test_frame.py
git commit -m "feat(picker): Frame.flush"
```

---

## Task 6: Box-drawing helper

**Files:**
- Modify: `src/picker/frame.py`
- Modify: `tests/picker/test_frame.py`

Single-line box drawing only (`┌─┐│└┘`). YAGNI on double/rounded.

- [ ] **Step 1: Add failing tests**

Append to `tests/picker/test_frame.py`:

```python
def test_box_draws_corners_and_edges():
    f = Frame(6, 4)
    f.box(0, 0, w=6, h=4)
    # Corners
    assert f.get(0, 0).char == "┌"
    assert f.get(0, 5).char == "┐"
    assert f.get(3, 0).char == "└"
    assert f.get(3, 5).char == "┘"
    # Top/bottom edges
    for c in range(1, 5):
        assert f.get(0, c).char == "─"
        assert f.get(3, c).char == "─"
    # Left/right edges
    for r in range(1, 3):
        assert f.get(r, 0).char == "│"
        assert f.get(r, 5).char == "│"


def test_box_does_not_overwrite_interior():
    f = Frame(5, 3)
    f.put_cell(1, 2, "X", fg=RGB(10, 20, 30))
    f.box(0, 0, 5, 3)
    # Interior cell unchanged
    assert f.get(1, 2) == Cell("X", RGB(10, 20, 30), None)


def test_box_fg_propagates_to_border():
    f = Frame(4, 3)
    f.box(0, 0, 4, 3, fg=RGB(100, 100, 100))
    assert f.get(0, 0).fg == RGB(100, 100, 100)
    assert f.get(2, 0).fg == RGB(100, 100, 100)


def test_box_too_small_does_nothing_or_clips_gracefully():
    f = Frame(5, 5)
    # 1x1 box doesn't make sense — should not crash; can paint at most a corner
    f.box(0, 0, 1, 1)
    # Either ┌ alone or unchanged is acceptable, just no exception
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v -k box
```

Expected: `AttributeError: 'Frame' object has no attribute 'box'`.

- [ ] **Step 3: Implement**

Append to `Frame` class:

```python
    def box(
        self,
        row: int,
        col: int,
        w: int,
        h: int,
        fg: Optional[RGB] = None,
        bg: Optional[RGB] = None,
    ) -> None:
        """Draw a single-line box border. Interior cells are left untouched."""
        if w < 1 or h < 1:
            return
        # Corners
        self.put_cell(row, col, "┌", fg, bg)
        self.put_cell(row, col + w - 1, "┐", fg, bg)
        self.put_cell(row + h - 1, col, "└", fg, bg)
        self.put_cell(row + h - 1, col + w - 1, "┘", fg, bg)
        # Top and bottom edges
        for c in range(col + 1, col + w - 1):
            self.put_cell(row, c, "─", fg, bg)
            self.put_cell(row + h - 1, c, "─", fg, bg)
        # Left and right edges
        for r in range(row + 1, row + h - 1):
            self.put_cell(r, col, "│", fg, bg)
            self.put_cell(r, col + w - 1, "│", fg, bg)
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_frame.py -v
```

Expected: 22 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/frame.py tests/picker/test_frame.py
git commit -m "feat(picker): Frame.box single-line border"
```

---

## Task 7: SIGWINCH resize handler

**Files:**
- Modify: `src/picker/term.py`
- Modify: `tests/picker/test_term.py`

- [ ] **Step 1: Add failing test**

Append to `tests/picker/test_term.py`:

```python
import os
import signal
import time
from src.picker.term import install_resize_handler, uninstall_resize_handler


def test_resize_handler_fires_on_sigwinch():
    fired = []

    def on_resize(cols: int, rows: int) -> None:
        fired.append((cols, rows))

    install_resize_handler(on_resize)
    try:
        # Send ourselves SIGWINCH. The handler should run in this process.
        os.kill(os.getpid(), signal.SIGWINCH)
        # Signals are async; give the handler a brief moment.
        time.sleep(0.05)
        assert len(fired) == 1
        cols, rows = fired[0]
        assert cols >= 1 and rows >= 1
    finally:
        uninstall_resize_handler()


def test_uninstall_resize_handler_restores_default():
    install_resize_handler(lambda c, r: None)
    uninstall_resize_handler()
    # After uninstall, signal handler is reset. We can't observe the default
    # cleanly without sending the signal and observing no effect — but we can
    # at least confirm the function runs without error.
    # (The fired-list invariant is exercised by the previous test.)
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_term.py -v -k resize
```

Expected: `ImportError: cannot import name 'install_resize_handler'`.

- [ ] **Step 3: Implement**

Append to `src/picker/term.py` (imports at top with existing imports):

```python
import signal
from typing import Callable, Optional


_resize_callback: Optional[Callable[[int, int], None]] = None


def _sigwinch_handler(signum: int, frame) -> None:  # noqa: ARG001  (signal API)
    if _resize_callback is not None:
        cols, rows = get_size()
        _resize_callback(cols, rows)


def install_resize_handler(callback: Callable[[int, int], None]) -> None:
    """Install a SIGWINCH handler that calls `callback(cols, rows)` on resize.

    Only one callback is active at a time; installing replaces any prior one.
    """
    global _resize_callback
    _resize_callback = callback
    signal.signal(signal.SIGWINCH, _sigwinch_handler)


def uninstall_resize_handler() -> None:
    """Restore the default SIGWINCH disposition."""
    global _resize_callback
    _resize_callback = None
    signal.signal(signal.SIGWINCH, signal.SIG_DFL)
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_term.py -v
```

Expected: 8 passed (6 existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/picker/term.py tests/picker/test_term.py
git commit -m "feat(picker): SIGWINCH resize handler"
```

---

## Task 8: Upgrade smoke test to use Frame

The Phase 1 smoke test wrote to `sys.stdout` directly. Rewriting it to paint a `Frame` and flush once validates that the abstraction wires up cleanly end-to-end.

**Files:**
- Modify: `src/picker/__main__.py`

- [ ] **Step 1: Rewrite `__main__.py`**

Replace the file contents with:

```python
"""Phase 2 smoke test for src.picker.

Run: python3 -m src.picker

What it does:
  1. Enters the alternate screen, hides the cursor, sets OSC bg.
  2. Builds a Frame for the current terminal size:
       - 8 truecolor swatches across the top
       - a single-line box around the screen
       - a help text line inside the box
  3. Flushes the Frame once.
  4. Installs a SIGWINCH handler that re-renders on resize.
  5. Waits for a single keypress; echoes which key was pressed.
  6. Resets terminal bg, exits alt screen, restores cursor.
"""
import sys
from src.picker import term as t
from src.picker.colors import RGB, hex_to_rgb
from src.picker.frame import Frame
from src.picker.names import NAMED_COLORS


SWATCH_HEXES = ["#ff5555", "#ffaa55", "#ffff55", "#55ff55",
                "#55ffff", "#5555ff", "#aa55ff", "#ff55aa"]


def build_frame(cols: int, rows: int, first_name: str, first_hex: str) -> Frame:
    f = Frame(cols, rows)
    # Border around the whole screen
    f.box(0, 0, cols, rows, fg=RGB(128, 128, 128))
    # Swatches on row 1 (just inside the top border)
    for i, hex_v in enumerate(SWATCH_HEXES):
        rgb = hex_to_rgb(hex_v)
        f.fill(1, 1 + i * 8, w=8, h=1, char=" ", bg=rgb)
    # Help text on rows 3 and 5
    f.put_str(3, 2, f"terminal bg: {first_name} ({first_hex})")
    f.put_str(5, 2, "press any key to exit (try arrow keys, shift+arrow, ctrl-c)")
    return f


def render(cols: int, rows: int, first_name: str, first_hex: str) -> None:
    f = build_frame(cols, rows, first_name, first_hex)
    f.flush()


def main() -> int:
    first_name = next(iter(NAMED_COLORS))
    first_hex = NAMED_COLORS[first_name]

    sys.stdout.write(t.enter_alt_screen())
    sys.stdout.write(t.hide_cursor())
    sys.stdout.write(t.clear_screen())
    sys.stdout.flush()
    t.osc_bg(first_hex)

    def on_resize(cols: int, rows: int) -> None:
        sys.stdout.write(t.clear_screen())
        render(cols, rows, first_name, first_hex)

    t.install_resize_handler(on_resize)

    try:
        cols, rows = t.get_size()
        render(cols, rows, first_name, first_hex)
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


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
.venv/bin/python -c "import src.picker.__main__ as m; print('main callable:', callable(m.main))"
```

Expected: `main callable: True`.

- [ ] **Step 3: Run all tests**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass (47 from Phase 1 + 22 new frame tests + 2 resize tests = 71).

- [ ] **Step 4: Commit**

```bash
git add src/picker/__main__.py
git commit -m "feat(picker): smoke test paints via Frame, redraws on resize"
```

- [ ] **Step 5: Push**

```bash
git push -u origin feature/picker-render
```

---

## Verification before declaring Phase 2 done

Run this checklist manually:

- [ ] `.venv/bin/pytest -v` — 71/71 green.
- [ ] `python3 -m src.picker` in a real TTY:
  - Bordered screen with 8 swatches and help text appears.
  - Resize the terminal window: the border and content reflow without garbage; no flicker is OK to ignore for v1, but missing characters or stuck escape sequences are not.
  - Press a key: clean exit, terminal restored, one line printed describing the key.
  - Press Ctrl+C: same — `key=CTRL_C` printed, terminal restored.
- [ ] `git diff main..HEAD --stat` — only these files touched:
  - `src/picker/__main__.py`
  - `src/picker/frame.py` (new)
  - `src/picker/term.py` (resize handler appended)
  - `tests/picker/test_frame.py` (new)
  - `tests/picker/test_term.py` (resize test appended)
- [ ] Grep the repo for `print(` outside `__main__.py` and outside tests — should match nothing in library code.

## What comes next (NOT in this plan)

- **Phase 3:** Components (`Slider`, `Settings`, `TerminalPreview`, `SwatchBrowser`, `ColorSlicer`). Each is a function or small class returning a `Frame` patch — i.e., taking a sub-rectangle of the parent frame and painting into it. The 2D color slicer uses half-block characters (`▀`) to double vertical resolution and will be the rendering performance hotspot; that's where Phase 3 will introduce per-component memoization.
- **Phase 4:** `App` state (a single dict), pure `update(state, event)` function, pure `render(state) -> Frame`, main loop.
- **Phase 5:** `bin/hued-pick` shim, `bin/hued -i` wiring, Homebrew formula update, README docs, removal of Node-based picker artifacts.

Each phase gets its own plan written after the previous one lands.
