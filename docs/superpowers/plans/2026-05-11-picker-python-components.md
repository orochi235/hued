# Picker Python Port — Phase 3: Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the five picker UI components as pure functions that paint into a parent `Frame` at a caller-supplied sub-rectangle. Each component has zero internal I/O; the caller owns the frame and decides where each panel lives.

**Architecture:** Each component is a module-level function with the signature `render_<name>(frame, row, col, w, h, **state) -> None`. Components call `frame.put_cell`, `frame.put_str`, `frame.fill`, and `frame.box` exclusively — no terminal I/O, no `sys.stdout`. The ColorSlicer is the performance hotspot; it uses a module-level LRU-style dict keyed on `(model, hex, view_idx, w, h)` to avoid recomputing the pixel grid on every frame.

**Tech Stack:** Python 3.9+ stdlib only, builds on Phase 1 (`src/picker/colors.py`, `src/picker/names.py`) and Phase 2 (`src/picker/frame.py`). No new runtime deps.

**Branch strategy:** Cut `feature/picker-components` from `main` after Phase 2 (`feature/picker-render`) merges. If Phase 2 has not yet merged when you start, cut from `feature/picker-render` instead and rebase when Phase 2 lands.

---

## File Structure

Files this plan creates or modifies:

- **Create:** `src/picker/components/__init__.py` — empty, marks the subpackage.
- **Create:** `src/picker/components/slider.py` — `render_slider(...)`.
- **Create:** `src/picker/components/settings.py` — `render_settings(...)`.
- **Create:** `src/picker/components/preview.py` — `render_terminal_preview(...)`.
- **Create:** `src/picker/components/swatch_browser.py` — `render_swatch_browser(...)`, `sort_entries(...)`.
- **Create:** `src/picker/components/slicer.py` — `render_color_slicer(...)`, `_SLICER_CACHE`, `_clear_slicer_cache()`.
- **Create:** `tests/picker/components/__init__.py` — empty.
- **Create:** `tests/picker/components/test_slider.py`
- **Create:** `tests/picker/components/test_settings.py`
- **Create:** `tests/picker/components/test_preview.py`
- **Create:** `tests/picker/components/test_swatch_browser.py`
- **Create:** `tests/picker/components/test_slicer.py`

After this phase:

```
src/picker/
  components/
    __init__.py
    slider.py
    settings.py
    preview.py
    swatch_browser.py
    slicer.py
  __init__.py
  __main__.py
  colors.py
  frame.py
  keys.py
  names.py
  term.py

tests/picker/
  components/
    __init__.py
    test_slider.py
    test_settings.py
    test_preview.py
    test_swatch_browser.py
    test_slicer.py
  test_colors.py
  test_frame.py
  test_keys.py
  test_names.py
  test_term.py
```

---

## Design decisions (read before implementing)

**Half-block rendering in the slicer:** `▀` (U+2580, UPPER HALF BLOCK) displays the upper half of a cell in the **foreground** color and the lower half in the **background** color. This means each terminal cell encodes two vertically stacked pixels. The slicer builds a grid of `(top_rgb, bottom_rgb)` tuples by computing two independent pixel colors per pair of screen rows, then calls `frame.put_cell(r, c, "▀", fg=top_rgb, bg=bottom_rgb)`. This halves the terminal-row count needed for a given visual resolution — 20 visible slicer rows produce 40 logical pixel rows.

**SwatchBrowser scroll:** The focused swatch is always kept visible. Scroll offset in rows (where each row is one display row of multi-column swatches) is: `scroll_row = max(0, focused_row_idx - (visible_rows - 1))` then clamped to `max(0, total_rows - visible_rows)`. This keeps the focused swatch at the bottom of the viewport during forward navigation and allows it to ride up as the list is exhausted. "Focused row index" is `focused_idx // num_cols`; "total rows" is `ceil(len(entries) / num_cols)`.

**Swatch layout:** Each named-color swatch is 4 characters wide (a 4-cell filled rectangle), with a 1-character gap between swatches. Number of columns: `num_cols = max(1, (w - 2) // 5)` (2 chars for left+right padding, each swatch+gap is 5 wide).

**SwatchBrowser sort modes:** `name` (alphabetical, as-is from `NAMED_COLORS`) and `hue` (sort by HSL hue, with near-achromatic colors — `s < 5` — sorted first by lightness). The TS prototype has many more sort modes; YAGNI — add them in Phase 4 if needed.

**SwatchBrowser filter:** Case-insensitive substring match on color name. `filter.lower() in name` is sufficient.

**Slicer memoization storage:** A module-level `_SLICER_CACHE: dict[tuple, list[list[tuple[RGB, RGB]]]] = {}`. The key is `(model_name, current_hex, view_idx, w, h)`. A companion `_clear_slicer_cache() -> None` function is provided for test teardown. There is no eviction; in practice the app renders at most a handful of distinct sizes and the cache stays small.

**Color model views:** The slicer supports four models with views matching the TS prototype. Each view is a named tuple `SlicerView(label_fn, pixel_fn, cursor_fn)`:
- **oklch:** H/C at fixed L; H/L at fixed C; C/L at fixed H; hue wheel at fixed L.
- **hsl:** H/S at fixed L; H/L at fixed S; S/L at fixed H; hue wheel at fixed L.
- **rgb:** R/G at fixed B; R/B at fixed G; G/B at fixed R.
- **lab:** a/b at fixed L; L/a at fixed b; L/b at fixed a; hue wheel at fixed L.

**Luma threshold:** Characters drawn on a colored background need a contrasting color. `luma = 0.299 * r + 0.7152 * g + 0.0722 * b`; if `luma > 128` use black (`RGB(0,0,0)`), else white (`RGB(255,255,255)`). This matches the TS prototype's formula.

**Focus accent color:** `RGB(0, 255, 255)` (cyan) for focused labels/values. Dim foreground for unfocused: `RGB(128, 128, 128)`.

**Slider layout constants:** `LABEL_W = 2` (e.g., `"R "`), `VALUE_W = 4` (e.g., `" 123"`), `SHADOW = RGB(26, 26, 26)` (`#1a1a1a`). Track width: `track_w = max(4, w - LABEL_W - VALUE_W)`.

**Slider rows:** The slider paints 3 terminal rows when a color function is supplied (matching the TS prototype's drop-shadow design):
- Row 0: label + color track (with `◆` marker at focused position) + value.
- Row 1: blank label + plain color track (no marker) + shadow cell at col `LABEL_W + track_w` + blank value.
- Row 2: wider shadow row spanning `LABEL_W + 1` blanks + `track_w` shadow cells.

When no color function is supplied (fallback), the slider paints 1 row using `█` for filled and `░` for empty.

**Settings panel:** Uses 1-cell internal padding on all sides (`fill` the interior, then write over it). Rows: model row (`RGB HSL OKLCH LAB` with active highlighted in cyan+bold), step row (`bg fg`), live indicator (`[✓] live` or `[ ] live`), hex+name row.

**TerminalPreview sample lines:** Four lines of simulated shell output inside a box, then a contrast-ratio line below the box:
```
~/project
$ git status
On branch main
$
```
All four lines painted with the supplied bg/fg.

---

## Task 1: Branch + components subpackage skeleton

**Files:**
- Create: `src/picker/components/__init__.py`
- Create: `tests/picker/components/__init__.py`

- [ ] **Step 1: Create branch from main**

```bash
git checkout main && git pull --ff-only
git checkout -b feature/picker-components
```

- [ ] **Step 2: Create empty package files**

```bash
mkdir -p src/picker/components tests/picker/components
touch src/picker/components/__init__.py tests/picker/components/__init__.py
```

- [ ] **Step 3: Verify pytest still passes**

```bash
.venv/bin/pytest -v
```

Expected: all existing tests pass (no new tests yet). If the venv does not exist: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` then retry.

- [ ] **Step 4: Commit**

```bash
git add src/picker/components/__init__.py tests/picker/components/__init__.py
git commit -m "chore(picker): scaffold components subpackage"
```

---

## Task 2: Slider

**Files:**
- Create: `src/picker/components/slider.py`
- Create: `tests/picker/components/test_slider.py`

### Design notes

The slider renders a horizontal color track with a position marker and drop shadow. The caller supplies a `get_color` callable that returns an `RGB` for each integer value on the track, allowing the track to be a gradient through color space.

Layout (with `get_color` supplied, `w=38`):

```
Row 0:  R  [track cells 34-wide with ◆ at position]  123
Row 1:     [track cells 34-wide, plain]█                    (shadow at track_w+1)
Row 2:      ██████████████████████████████████              (shadow row, track_w wide)
```

Constants: `LABEL_W = 2`, `VALUE_W = 4`, `SHADOW_RGB = RGB(26, 26, 26)`.
Track width: `track_w = max(4, w - LABEL_W - VALUE_W)`.

- [ ] **Step 1: Write failing tests**

Create `tests/picker/components/test_slider.py`:

```python
from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.slider import render_slider


def _frame(w=40, h=5):
    return Frame(w, h)


def test_slider_paints_label_at_col0():
    f = _frame()
    render_slider(f, row=0, col=0, w=38, h=3, label="R", value=128, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Label "R " starts at col 0, row 0
    assert f.get(0, 0).char == "R"
    assert f.get(0, 1).char == " "


def test_slider_paints_value_right_aligned():
    f = _frame()
    # value=255 -> " 255" in the last VALUE_W=4 columns starting at col LABEL_W+track_w
    render_slider(f, row=0, col=0, w=38, h=3, label="R", value=255, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    LABEL_W, VALUE_W = 2, 4
    track_w = max(4, 38 - LABEL_W - VALUE_W)
    value_col = LABEL_W + track_w
    text_in_frame = "".join(f.get(0, value_col + i).char for i in range(VALUE_W))
    assert text_in_frame == " 255"


def test_slider_track_cells_have_bg_color():
    f = _frame()
    render_slider(f, row=0, col=0, w=38, h=3, label="G", value=0, max=255,
                  get_color=lambda v: RGB(0, v, 0))
    # Track starts at col LABEL_W=2; the first cell is for value 0 -> RGB(0,0,0)
    cell = f.get(0, 2)
    assert cell.bg == RGB(0, 0, 0)


def test_slider_marker_at_correct_position():
    f = _frame()
    # value=0 -> marker at leftmost track position (col LABEL_W)
    render_slider(f, row=0, col=0, w=38, h=3, label="B", value=0, max=255,
                  focused=True, get_color=lambda v: RGB(0, 0, v))
    assert f.get(0, 2).char == "◆"


def test_slider_no_marker_when_not_focused():
    f = _frame()
    render_slider(f, row=0, col=0, w=38, h=3, label="B", value=0, max=255,
                  focused=False, get_color=lambda v: RGB(0, 0, v))
    # No ◆ in track row
    LABEL_W = 2
    assert f.get(0, LABEL_W).char != "◆"


def test_slider_shadow_row1_has_shadow_cell():
    f = _frame()
    LABEL_W, VALUE_W = 2, 4
    w = 38
    track_w = max(4, w - LABEL_W - VALUE_W)
    render_slider(f, row=0, col=0, w=w, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Row 1: shadow cell appears at col LABEL_W + track_w
    shadow_cell = f.get(1, LABEL_W + track_w)
    assert shadow_cell.bg == RGB(26, 26, 26)


def test_slider_shadow_row2_has_shadow_strip():
    f = _frame()
    LABEL_W, VALUE_W = 2, 4
    w = 38
    track_w = max(4, w - LABEL_W - VALUE_W)
    render_slider(f, row=0, col=0, w=w, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Row 2 shadow starts at col LABEL_W+1 and is track_w wide
    for c in range(track_w):
        assert f.get(2, LABEL_W + 1 + c).bg == RGB(26, 26, 26)


def test_slider_col_offset_respected():
    f = _frame(w=50)
    render_slider(f, row=1, col=5, w=38, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Label starts at col 5, not col 0
    assert f.get(1, 5).char == "R"
    assert f.get(1, 0).char == " "  # untouched


def test_slider_fallback_no_get_color():
    f = _frame()
    # When get_color is None, slider paints 1 row: filled blocks + empty blocks
    render_slider(f, row=0, col=0, w=38, h=1, label="R", value=128, max=255,
                  get_color=None)
    # Row 0 should contain at least one '█' and one '░'
    row_chars = [f.get(0, c).char for c in range(38)]
    assert "█" in row_chars
    assert "░" in row_chars


def test_slider_out_of_bounds_rows_dont_crash():
    # Frame has only 2 rows but slider requests 3; rows 2+ are silently clipped
    f = Frame(40, 2)
    render_slider(f, row=0, col=0, w=38, h=3, label="R", value=0, max=255,
                  get_color=lambda v: RGB(v, 0, 0))
    # Row 0 should still be painted
    assert f.get(0, 0).char == "R"
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/pytest tests/picker/components/test_slider.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.components.slider'`.

- [ ] **Step 3: Implement `src/picker/components/slider.py`**

Create `src/picker/components/slider.py`:

```python
from __future__ import annotations
from typing import Callable, Optional
from src.picker.frame import Frame
from src.picker.colors import RGB

LABEL_W = 2   # "R " — label is padded/truncated to this width
VALUE_W = 4   # " 123" — right-aligned value, 4 chars wide
SHADOW_RGB = RGB(26, 26, 26)  # #1a1a1a


def _luma(rgb: RGB) -> float:
    return 0.299 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _contrast(bg: RGB) -> RGB:
    """Return black or white for readable text on `bg`."""
    return RGB(0, 0, 0) if _luma(bg) > 128 else RGB(255, 255, 255)


def render_slider(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    label: str,
    value: int,
    max: int,
    focused: bool = False,
    track_color: RGB = RGB(255, 255, 255),
    get_color: Optional[Callable[[int], RGB]] = None,
) -> None:
    """Paint a single-channel slider into `frame` at (row, col, w, h).

    With `get_color` supplied the slider renders 3 rows:
      Row 0: label + gradient track with ◆ marker at current value + right-aligned value
      Row 1: blank label + plain gradient track + one shadow cell to the right
      Row 2: blank (LABEL_W+1 chars) + shadow strip (track_w wide)

    Without `get_color` the slider renders 1 row using █/░ fill characters.
    The `h` parameter is accepted for interface uniformity but does not expand the
    component beyond its natural height — excess rows are simply unused.

    All out-of-bounds paints are silently clipped by Frame.
    """
    track_w = max(4, w - LABEL_W - VALUE_W)
    # Position of the marker (0-indexed within the track)
    pos = round((value / max) * (track_w - 1)) if max > 0 else 0

    accent = RGB(0, 255, 255) if focused else RGB(128, 128, 128)
    label_str = (label + " " * LABEL_W)[:LABEL_W]
    value_str = str(value).rjust(VALUE_W)

    if get_color is not None:
        # --- Row 0: label + track + value ---
        frame.put_str(row, col, label_str, fg=accent)
        for i in range(track_w):
            cell_val = round((i / (track_w - 1)) * max) if track_w > 1 else value
            bg = get_color(cell_val)
            char = "◆" if (i == pos and focused) else " "
            fg = _contrast(bg) if (i == pos and focused) else bg
            frame.put_cell(row, col + LABEL_W + i, char, fg=fg, bg=bg)
        frame.put_str(row, col + LABEL_W + track_w, value_str, fg=accent)

        # --- Row 1: blank label + plain track + shadow cell ---
        frame.put_str(row + 1, col, " " * LABEL_W)
        for i in range(track_w):
            cell_val = round((i / (track_w - 1)) * max) if track_w > 1 else value
            bg = get_color(cell_val)
            frame.put_cell(row + 1, col + LABEL_W + i, " ", bg=bg)
        # Shadow cell at track_w (just past end of track)
        frame.put_cell(row + 1, col + LABEL_W + track_w, " ", bg=SHADOW_RGB)
        # Fill remainder of value area with spaces
        frame.put_str(row + 1, col + LABEL_W + track_w + 1, " " * (VALUE_W - 1))

        # --- Row 2: wide shadow strip ---
        frame.put_str(row + 2, col, " " * (LABEL_W + 1))
        frame.fill(row + 2, col + LABEL_W + 1, track_w, 1, " ", bg=SHADOW_RGB)
        frame.put_str(row + 2, col + LABEL_W + 1 + track_w, " " * (VALUE_W - 1))

    else:
        # Fallback: 1-row block-bar
        frame.put_str(row, col, label_str, fg=accent)
        filled = round((value / max) * track_w) if max > 0 else 0
        frame.put_str(row, col + LABEL_W, "█" * filled,
                      fg=track_color if focused else RGB(128, 128, 128))
        frame.put_str(row, col + LABEL_W + filled, "░" * (track_w - filled),
                      fg=RGB(64, 64, 64))
        frame.put_str(row, col + LABEL_W + track_w, value_str, fg=accent)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/components/test_slider.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/components/slider.py tests/picker/components/test_slider.py
git commit -m "feat(picker): render_slider component"
```

---

## Task 3: Settings panel

**Files:**
- Create: `src/picker/components/settings.py`
- Create: `tests/picker/components/test_settings.py`

### Design notes

The settings panel shows four stacked rows of information inside the supplied rectangle:

```
Row 0:  (blank top padding)
Row 1:   RGB  HSL  OKLCH  LAB           <- active model is cyan+bold, others dimmed
Row 2:   bg  fg                         <- active step is cyan, other dimmed
Row 3:   [✓] live  (or [ ] live)        <- green when live, gray otherwise
Row 4:   #1a0a0a  ≈ midnight blue       <- hex in cyan, name dimmed
Row 5:  (blank bottom padding)
```

`w` and `h` are respected: text is clipped to the frame. The row offsets above are relative to the component's `row` parameter.

- [ ] **Step 1: Write failing tests**

Create `tests/picker/components/test_settings.py`:

```python
from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.settings import render_settings


def _frame(w=30, h=8):
    return Frame(w, h)


def test_settings_active_model_painted_at_row1():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#ff0000", nearest_name="red")
    # "RGB" should appear on row 1 starting at col 1 (1-char padding)
    row1 = "".join(f.get(1, c).char for c in range(30))
    assert "RGB" in row1


def test_settings_all_models_appear():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="hsl", step="fg", live=False,
                    current_hex="#00ff00", nearest_name="lime")
    row1 = "".join(f.get(1, c).char for c in range(30))
    for model_text in ("RGB", "HSL", "OKLCH", "LAB"):
        assert model_text in row1, f"missing {model_text!r} in row1: {row1!r}"


def test_settings_active_model_is_cyan():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="oklch", step="bg", live=True,
                    current_hex="#0000ff", nearest_name="blue")
    # The 'O' of OKLCH should be cyan
    row1 = "".join(f.get(1, c).char for c in range(30))
    idx = row1.index("O")
    assert f.get(1, idx).fg == RGB(0, 255, 255)


def test_settings_active_step_is_cyan():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="fg", live=False,
                    current_hex="#ffffff", nearest_name="white")
    row2 = "".join(f.get(2, c).char for c in range(30))
    idx = row2.index("f")  # 'fg' starts with 'f'
    # The 'f' of 'fg' should be cyan
    assert f.get(2, idx).fg == RGB(0, 255, 255)


def test_settings_live_indicator_checked():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#ff0000", nearest_name="red")
    row3 = "".join(f.get(3, c).char for c in range(30))
    assert "✓" in row3


def test_settings_live_indicator_unchecked():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=False,
                    current_hex="#ff0000", nearest_name="red")
    row3 = "".join(f.get(3, c).char for c in range(30))
    assert "✓" not in row3
    assert "[" in row3 and "]" in row3


def test_settings_hex_appears_on_row4():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#aabbcc", nearest_name="something")
    row4 = "".join(f.get(4, c).char for c in range(30))
    assert "#aabbcc" in row4


def test_settings_nearest_name_appears_on_row4():
    f = _frame()
    render_settings(f, row=0, col=0, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#aabbcc", nearest_name="powderblue")
    row4 = "".join(f.get(4, c).char for c in range(30))
    assert "powderblue" in row4


def test_settings_col_offset():
    f = Frame(40, 8)
    render_settings(f, row=0, col=5, w=30, h=8,
                    model="rgb", step="bg", live=True,
                    current_hex="#ff0000", nearest_name="red")
    # col 0-4 untouched
    assert f.get(1, 0).char == " "
    # The model label begins at col 6 (col=5 + 1 padding)
    row1 = "".join(f.get(1, c).char for c in range(40))
    assert "RGB" in row1
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/pytest tests/picker/components/test_settings.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.components.settings'`.

- [ ] **Step 3: Implement `src/picker/components/settings.py`**

Create `src/picker/components/settings.py`:

```python
from __future__ import annotations
from src.picker.frame import Frame
from src.picker.colors import RGB

_CYAN = RGB(0, 255, 255)
_DIM = RGB(128, 128, 128)
_GREEN = RGB(0, 200, 0)

_MODELS = ("rgb", "hsl", "oklch", "lab")
_MODEL_LABELS = {"rgb": "RGB", "hsl": "HSL", "oklch": "OKLCH", "lab": "LAB"}


def render_settings(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    model: str,
    step: str,
    live: bool,
    current_hex: str,
    nearest_name: str,
) -> None:
    """Paint the settings info panel into `frame` at (row, col, w, h).

    Layout (relative rows):
      row+0: blank (top padding)
      row+1: model selector  — RGB HSL OKLCH LAB, active in cyan
      row+2: step selector   — bg  fg, active in cyan
      row+3: live indicator  — [✓] live  or  [ ] live
      row+4: hex + name      — #rrggbb  ≈ name
      row+5: blank (bottom padding)
    """
    pad = col + 1  # 1-char left padding

    # Row 0: clear the band
    frame.fill(row, col, w, 1, " ")

    # Row 1: model selector
    frame.fill(row + 1, col, w, 1, " ")
    c = pad
    for m in _MODELS:
        label = _MODEL_LABELS[m] + " "
        fg = _CYAN if m == model else _DIM
        frame.put_str(row + 1, c, label, fg=fg)
        c += len(label)

    # Row 2: step selector
    frame.fill(row + 2, col, w, 1, " ")
    frame.put_str(row + 2, pad, "bg", fg=_CYAN if step == "bg" else _DIM)
    frame.put_str(row + 2, pad + 3, "fg", fg=_CYAN if step == "fg" else _DIM)

    # Row 3: live indicator
    frame.fill(row + 3, col, w, 1, " ")
    check = "✓" if live else " "
    live_fg = _GREEN if live else _DIM
    frame.put_str(row + 3, pad, f"[{check}] live", fg=live_fg)

    # Row 4: hex + nearest name
    frame.fill(row + 4, col, w, 1, " ")
    frame.put_str(row + 4, pad, current_hex, fg=_CYAN)
    frame.put_str(row + 4, pad + len(current_hex) + 1, f"≈ {nearest_name}", fg=_DIM)

    # Row 5: blank
    frame.fill(row + 5, col, w, 1, " ")
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/components/test_settings.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/components/settings.py tests/picker/components/test_settings.py
git commit -m "feat(picker): render_settings component"
```

---

## Task 4: TerminalPreview

**Files:**
- Create: `src/picker/components/preview.py`
- Create: `tests/picker/components/test_preview.py`

### Design notes

The preview component shows a simulated terminal session inside a box, then displays contrast-ratio and WCAG compliance indicators below the box.

Layout (all coordinates relative to component `row`, `col`):

```
row+0:  ┌─────────────────────────┐
row+1:  │ ~/project               │   <- bg/fg
row+2:  │ $ git status            │   <- bg/fg
row+3:  │ On branch main          │   <- bg/fg, dimmer (still same fg, renderer uses same fg)
row+4:  │ $                       │   <- bg/fg
row+5:  └─────────────────────────┘
row+6:  (blank)
row+7:   4.5:1  AA✓  AAA✗         <- contrast ratio and WCAG badges
row+8:   bg #rrggbb  fg #rrggbb
```

The box uses `frame.box`. The interior fill uses `frame.fill` with `bg=bg_rgb`, then `frame.put_str` to write the text with `fg=fg_rgb, bg=bg_rgb` so that partial lines have the right background.

**Contrast ratio formula:** `(lighter + 0.05) / (darker + 0.05)` where lighter/darker are the WCAG relative luminances of the two colors. WCAG relative luminance: for each channel `v` in `[0,1]`, `L = v/12.92` if `v <= 0.03928` else `((v+0.055)/1.055)^2.4`; then `Y = 0.2126*R + 0.7152*G + 0.0722*B`.

- [ ] **Step 1: Write failing tests**

Create `tests/picker/components/test_preview.py`:

```python
from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.preview import render_terminal_preview


def _frame(w=30, h=12):
    return Frame(w, h)


def test_preview_box_top_left_corner():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    assert f.get(0, 0).char == "┌"


def test_preview_box_top_right_corner():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    assert f.get(0, 29).char == "┐"


def test_preview_interior_has_bg_color():
    f = _frame()
    bg = RGB(30, 30, 80)
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#1e1e50", fg_hex="#ffffff")
    # Interior starts at row 1, col 1 inside the box
    assert f.get(1, 1).bg == bg


def test_preview_interior_text_has_fg_color():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#00ff00")
    # Row 1 has the first sample text line with the fg color
    assert f.get(1, 2).fg == RGB(0, 255, 0)


def test_preview_sample_text_present():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    # "~/project" must appear somewhere on interior row 1
    row1 = "".join(f.get(1, c).char for c in range(30))
    assert "~/project" in row1


def test_preview_contrast_ratio_line_appears():
    f = _frame()
    # Black bg, white fg -> very high contrast
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    # Ratio line is at row 7 (box rows 0-5, blank row 6, ratio row 7)
    row7 = "".join(f.get(7, c).char for c in range(30))
    assert ":1" in row7


def test_preview_aa_pass_green_for_high_contrast():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    # "AA✓" should appear on the ratio line
    row7 = "".join(f.get(7, c).char for c in range(30))
    assert "AA✓" in row7


def test_preview_aa_fail_for_low_contrast():
    f = _frame()
    # Very similar colors -> fails AA (ratio << 4.5)
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#888888", fg_hex="#999999")
    row7 = "".join(f.get(7, c).char for c in range(30))
    assert "AA✗" in row7


def test_preview_hex_line_shows_both_hexes():
    f = _frame()
    render_terminal_preview(f, row=0, col=0, w=30, h=12,
                            bg_hex="#1a2b3c", fg_hex="#eeddcc")
    row8 = "".join(f.get(8, c).char for c in range(30))
    assert "#1a2b3c" in row8
    assert "#eeddcc" in row8


def test_preview_col_offset():
    f = Frame(40, 12)
    render_terminal_preview(f, row=0, col=5, w=30, h=12,
                            bg_hex="#000000", fg_hex="#ffffff")
    assert f.get(0, 5).char == "┌"
    assert f.get(0, 0).char == " "  # untouched
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/pytest tests/picker/components/test_preview.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.components.preview'`.

- [ ] **Step 3: Implement `src/picker/components/preview.py`**

Create `src/picker/components/preview.py`:

```python
from __future__ import annotations
import math
from src.picker.frame import Frame
from src.picker.colors import RGB, hex_to_rgb

_CYAN = RGB(0, 255, 255)
_DIM = RGB(128, 128, 128)
_GREEN = RGB(0, 200, 0)
_YELLOW = RGB(200, 200, 0)
_RED = RGB(200, 0, 0)

_SAMPLE_LINES = [
    "~/project",
    "$ git status",
    "On branch main",
    "$",
]


def _relative_luminance(rgb: RGB) -> float:
    """WCAG 2.1 relative luminance for an sRGB color."""
    def lin(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(rgb.r) + 0.7152 * lin(rgb.g) + 0.0722 * lin(rgb.b)


def _contrast_ratio(rgb1: RGB, rgb2: RGB) -> float:
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def render_terminal_preview(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    bg_hex: str,
    fg_hex: str,
) -> None:
    """Paint a simulated terminal preview into `frame` at (row, col, w, h).

    Layout (rows relative to `row`):
      row+0..row+5:  single-line box with 4 sample text rows inside
      row+6:         blank
      row+7:         contrast ratio line  e.g.  21.0:1  AA✓  AAA✓
      row+8:         bg #hex  fg #hex
    """
    bg_rgb = hex_to_rgb(bg_hex)
    fg_rgb = hex_to_rgb(fg_hex)

    # Box: occupies rows 0-5, full width
    box_h = 6
    frame.box(row, col, w, box_h, fg=_DIM)

    # Interior: rows 1-4 (inside the box), cols col+1..col+w-2
    inner_w = max(0, w - 2)
    for r_off, line in enumerate(_SAMPLE_LINES):
        r = row + 1 + r_off
        # Fill whole interior row with the bg color first
        frame.fill(r, col + 1, inner_w, 1, " ", bg=bg_rgb)
        # Prepend a space for left padding inside the box
        text = " " + line
        frame.put_str(r, col + 1, text[:inner_w], fg=fg_rgb, bg=bg_rgb)

    # Row 6: blank
    frame.fill(row + 6, col, w, 1, " ")

    # Row 7: contrast ratio + WCAG badges
    ratio = _contrast_ratio(bg_rgb, fg_rgb)
    ratio_str = f"{ratio:.1f}:1"
    aa = ratio >= 4.5
    aaa = ratio >= 7.0
    aa_badge = "AA✓" if aa else "AA✗"
    aaa_badge = "AAA✓" if aaa else "AAA✗"
    aa_fg = _GREEN if aa else _RED
    aaa_fg = _GREEN if aaa else _DIM
    ratio_fg = _GREEN if aa else _YELLOW

    frame.fill(row + 7, col, w, 1, " ")
    c = col + 1
    frame.put_str(row + 7, c, ratio_str, fg=ratio_fg)
    c += len(ratio_str) + 2
    frame.put_str(row + 7, c, aa_badge, fg=aa_fg)
    c += len(aa_badge) + 2
    frame.put_str(row + 7, c, aaa_badge, fg=aaa_fg)

    # Row 8: bg/fg hex values
    frame.fill(row + 8, col, w, 1, " ")
    c = col + 1
    frame.put_str(row + 8, c, "bg ", fg=_DIM)
    c += 3
    frame.put_str(row + 8, c, bg_hex, fg=_CYAN)
    c += len(bg_hex) + 2
    frame.put_str(row + 8, c, "fg ", fg=_DIM)
    c += 3
    frame.put_str(row + 8, c, fg_hex, fg=_CYAN)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/components/test_preview.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/components/preview.py tests/picker/components/test_preview.py
git commit -m "feat(picker): render_terminal_preview component"
```

---

## Task 5: SwatchBrowser

**Files:**
- Create: `src/picker/components/swatch_browser.py`
- Create: `tests/picker/components/test_swatch_browser.py`

### Design notes

The SwatchBrowser renders a scrollable, filterable, sortable grid of named color swatches. Each swatch is 4 characters wide, gap of 1 between swatches, 1-char padding on the left. Number of columns: `num_cols = max(1, (w - 2) // 5)`. Each swatch occupies 2 terminal rows (tall swatch visual). A status line appears at the bottom.

Scroll formula: `focused_row = focused_idx // num_cols`; `scroll_row = max(0, min(focused_row, total_rows - visible_rows))`; visible rows count: `visible_rows = max(1, (h - 1) // 2)` (leave 1 row for status, each swatch is 2 rows tall).

Sort modes available: `"name"` (dict order, which is insertion-sorted alphabetically in NAMED_COLORS) and `"hue"` (near-achromatic colors with `HSL.s < 5` sorted first by lightness, then remaining sorted by hue, then saturation, then lightness).

The `focused_idx` is an index into the *filtered and sorted* list. The component does not own the focus index — the caller passes it in. The component paints a `◆` marker inside the focused swatch and uses a contrasting fg color for it.

- [ ] **Step 1: Write failing tests**

Create `tests/picker/components/test_swatch_browser.py`:

```python
from src.picker.frame import Frame
from src.picker.colors import RGB
from src.picker.components.swatch_browser import render_swatch_browser, sort_entries


COLORS = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "black": "#000000",
    "white": "#ffffff",
}


def _frame(w=30, h=12):
    return Frame(w, h)


# --- sort_entries tests ---

def test_sort_name_preserves_order():
    entries = list(COLORS.items())
    result = sort_entries(entries, "name")
    assert [n for n, _ in result] == list(COLORS.keys())


def test_sort_hue_puts_achromatic_first():
    result = sort_entries(list(COLORS.items()), "hue")
    names = [n for n, _ in result]
    # black and white are achromatic (s < 5 in HSL); they must come before hued colors
    assert names.index("black") < names.index("red")
    assert names.index("white") < names.index("red")


def test_sort_hue_orders_hued_by_hue():
    result = sort_entries(list(COLORS.items()), "hue")
    # red (hue~0), green (hue~120), blue (hue~240)
    names = [n for n, _ in result]
    hued = [n for n in names if n not in ("black", "white")]
    assert hued.index("red") < hued.index("green") < hued.index("blue")


# --- render_swatch_browser tests ---

def test_swatch_browser_paints_swatch_bg():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # The first swatch (red) should start at col 1, rows 0-1 with bg RGB(255,0,0)
    cell = f.get(0, 1)
    assert cell.bg == RGB(255, 0, 0)


def test_swatch_browser_focused_marker():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # First swatch row 0 should contain ◆ somewhere in cols 1-4
    row0 = [f.get(0, c).char for c in range(1, 5)]
    assert "◆" in row0


def test_swatch_browser_no_marker_on_unfocused():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=1)
    # First swatch (idx 0) should NOT have ◆
    row0 = [f.get(0, c).char for c in range(1, 5)]
    assert "◆" not in row0


def test_swatch_browser_filter_reduces_items():
    f = _frame()
    # Only "red" matches "re"
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="re", sort_mode="name",
                          focused_idx=0)
    # Green swatch (bg #00ff00) should NOT appear — check a different col range
    # With only 1 match the second swatch position (cols 6-9) should be empty/default
    num_cols = max(1, (30 - 2) // 5)
    if num_cols >= 2:
        second_cell = f.get(0, 1 + 5)  # second swatch starts at col 6
        # It should not have bg RGB(0,255,0) because green was filtered out
        assert second_cell.bg != RGB(0, 255, 0)


def test_swatch_browser_status_line_shows_name():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # Status line is the last row used; find it by checking for "red" in the bottom rows
    found = False
    for r in range(10, 12):
        row_text = "".join(f.get(r, c).char for c in range(30))
        if "red" in row_text:
            found = True
            break
    assert found, "status line showing focused color name not found"


def test_swatch_browser_scroll_keeps_focused_visible():
    # With a tall-enough browser and many colors, scrolling should keep the
    # focused swatch visible. Use 10 colors and focus on the 9th.
    many = {f"color{i:02d}": f"#{i*25:02x}{i*10:02x}{i*5:02x}" for i in range(10)}
    f = Frame(30, 12)
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors=many, filter_str="", sort_mode="name",
                          focused_idx=8)
    # Should not raise and should paint something (focused swatch must be visible)
    # Check that ◆ appears somewhere in the painted area
    marker_found = any(
        f.get(r, c).char == "◆"
        for r in range(10)
        for c in range(30)
    )
    assert marker_found


def test_swatch_browser_no_colors_no_crash():
    f = _frame()
    render_swatch_browser(f, row=0, col=0, w=30, h=12,
                          colors={}, filter_str="", sort_mode="name",
                          focused_idx=0)
    # Must not raise; paints "no results" or stays blank


def test_swatch_browser_row_col_offset():
    f = Frame(40, 16)
    render_swatch_browser(f, row=2, col=5, w=30, h=12,
                          colors=COLORS, filter_str="", sort_mode="name",
                          focused_idx=0)
    # First swatch starts at row=2, col=5+1=6
    assert f.get(2, 6).bg == RGB(255, 0, 0)
    # row 0 untouched
    assert f.get(0, 6).char == " "
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/pytest tests/picker/components/test_swatch_browser.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.components.swatch_browser'`.

- [ ] **Step 3: Implement `src/picker/components/swatch_browser.py`**

Create `src/picker/components/swatch_browser.py`:

```python
from __future__ import annotations
import math
from typing import List, Tuple
from src.picker.frame import Frame
from src.picker.colors import RGB, hex_to_rgb, rgb_to_hsl

_CYAN = RGB(0, 255, 255)
_DIM = RGB(128, 128, 128)
_YELLOW = RGB(200, 200, 0)

SortMode = str  # "name" | "hue"


def _luma(rgb: RGB) -> float:
    return 0.299 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _contrast(bg: RGB) -> RGB:
    return RGB(0, 0, 0) if _luma(bg) > 128 else RGB(255, 255, 255)


def sort_entries(
    entries: List[Tuple[str, str]],
    mode: SortMode,
) -> List[Tuple[str, str]]:
    """Sort (name, hex) pairs by `mode`.

    mode="name": return in original order (NAMED_COLORS is already alphabetical).
    mode="hue":  near-achromatic (HSL saturation < 5) sorted by lightness first,
                 then remaining sorted by hue, then saturation, then lightness.
    """
    if mode == "name":
        return list(entries)

    if mode == "hue":
        def hue_key(item: Tuple[str, str]):
            _, hex_val = item
            hsl = rgb_to_hsl(hex_to_rgb(hex_val))
            if hsl.s < 5:
                # Achromatic: sort before hued colors, by lightness
                return (0, hsl.l, 0.0, 0.0)
            return (1, hsl.h, hsl.s, hsl.l)
        return sorted(entries, key=hue_key)

    return list(entries)


def render_swatch_browser(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    colors: dict[str, str],
    filter_str: str,
    sort_mode: SortMode,
    focused_idx: int,
) -> None:
    """Paint a scrollable color swatch grid into `frame` at (row, col, w, h).

    Each swatch is 4 characters wide, with a 1-char gap between swatches and
    1-char left padding. Each swatch occupies 2 terminal rows. The bottom row
    of the component area is a status line showing the focused color name and hex.

    `focused_idx` is an index into the filtered+sorted color list. The caller
    is responsible for clamping it to the valid range before calling.
    """
    # 1. Filter
    filtered = [(n, h) for n, h in colors.items()
                if filter_str.lower() in n.lower()]

    # 2. Sort
    entries = sort_entries(filtered, sort_mode)

    # 3. Layout
    num_cols = max(1, (w - 2) // 5)  # each swatch+gap is 5 wide; 2 chars padding
    # Each swatch is 2 terminal rows tall; leave 1 row for status line
    visible_rows = max(1, (h - 1) // 2)

    if not entries:
        frame.fill(row, col, w, h, " ")
        frame.put_str(row, col + 1, "no results", fg=_DIM)
        return

    # 4. Scroll
    focused_clamped = max(0, min(focused_idx, len(entries) - 1))
    focused_row_in_grid = focused_clamped // num_cols
    total_rows = math.ceil(len(entries) / num_cols)
    scroll_row = max(0, min(focused_row_in_grid, total_rows - visible_rows))

    # 5. Paint swatch grid
    for vr in range(visible_rows):
        grid_row = scroll_row + vr
        row_entries_start = grid_row * num_cols
        row_entries = entries[row_entries_start: row_entries_start + num_cols]
        abs_row_top = row + vr * 2      # first terminal row of this swatch row
        abs_row_bot = abs_row_top + 1   # second terminal row (lower half of swatch)

        # Clear these two rows first
        frame.fill(abs_row_top, col, w, 1, " ")
        frame.fill(abs_row_bot, col, w, 1, " ")

        for ci, (name, hex_val) in enumerate(row_entries):
            abs_idx = grid_row * num_cols + ci
            is_focused = (abs_idx == focused_clamped)
            bg = hex_to_rgb(hex_val)
            swatch_col = col + 1 + ci * 5  # 1-char left pad, then 5 per swatch

            # Top row of swatch: show ◆ marker for focused
            for sc in range(4):
                if is_focused and sc == 0:
                    char = "◆"
                    fg = _contrast(bg)
                else:
                    char = " "
                    fg = bg  # invisible fg
                frame.put_cell(abs_row_top, swatch_col + sc, char, fg=fg, bg=bg)

            # Bottom row of swatch: plain fill
            frame.fill(abs_row_bot, swatch_col, 4, 1, " ", bg=bg)

    # 6. Status line: last row
    status_row = row + h - 1
    frame.fill(status_row, col, w, 1, " ")
    if 0 <= focused_clamped < len(entries):
        name, hex_val = entries[focused_clamped]
        frame.put_str(status_row, col + 1, name, fg=_CYAN)
        c = col + 1 + len(name) + 2
        frame.put_str(status_row, c, hex_val, fg=_DIM)
        c += len(hex_val) + 2
        frame.put_str(status_row, c, f"sort:{sort_mode}", fg=_DIM)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/components/test_swatch_browser.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/components/swatch_browser.py tests/picker/components/test_swatch_browser.py
git commit -m "feat(picker): render_swatch_browser component"
```

---

## Task 6: ColorSlicer — base rendering

**Files:**
- Create: `src/picker/components/slicer.py`
- Create: `tests/picker/components/test_slicer.py`

### Design notes

**Half-block rendering:** Each terminal cell displays two vertically stacked pixels. The character `▀` (U+2580, UPPER HALF BLOCK) renders its upper half in the cell's **foreground** color and its lower half in the cell's **background** color. So painting `frame.put_cell(r, c, "▀", fg=top_rgb, bg=bottom_rgb)` shows `top_rgb` in the top pixel and `bottom_rgb` in the bottom pixel. This means a grid of `pixel_h` logical pixel rows maps to `pixel_h // 2` terminal rows (pairs of pixel rows are collapsed into one terminal row). If `pixel_h` is odd, the last pixel row is shown alone; use `▀` with `fg=pixel_rgb` and `bg=RGB(0,0,0)`.

**Grid dimensions:**
- Terminal rows available for the slicer image: `grid_term_rows = max(1, h - 2)` (subtract 1 for the label row at the bottom, 1 for top margin). Each terminal row encodes 2 pixel rows. Total logical pixel rows: `pixel_h = grid_term_rows * 2`.
- Logical pixel columns: `pixel_w = max(1, w)` (one pixel per terminal column).

**Coordinate mapping:** For pixel at `(px, py)` where `px` is 0-indexed column and `py` is 0-indexed row from the top of the pixel grid:
- `xn = px / (pixel_w - 1)` if `pixel_w > 1` else `0.0` — normalized x (0=left, 1=right)
- `yn = 1.0 - py / (pixel_h - 1)` if `pixel_h > 1` else `1.0` — normalized y (0=bottom, 1=top — yn decreases as we go down visually)

**Cursor marker:** After computing the grid, paint a `◆` at the cursor position. The cursor's terminal row is `cy // 2` (where `cy` is the pixel-row index of the cursor); if `cy` is even it's the top pixel of the half-block cell, if `cy` is odd it's the bottom pixel. The cursor column is `cx`. Adjust fg/bg accordingly so the cursor is visible.

**Views data structure:** A `SlicerView` namedtuple with fields:
- `label_fn: Callable[..., str]` — receives the per-model current values and returns a label string.
- `pixel_fn: Callable[[float, float, ...], Optional[RGB]]` — receives `(xn, yn, current_rgb, current_hsl, current_oklch, current_lab)` and returns the color at that pixel, or `None` for out-of-gamut (paint as `RGB(17, 17, 17)` = `#111111`).
- `cursor_fn: Callable[..., Tuple[float, float]]` — receives the per-model values and returns `(cxn, cyn)` in `[0,1]x[0,1]` (same coordinate system as `xn`/`yn`).

The module defines a `VIEWS` dict mapping model name to a list of `SlicerView`.

**Out-of-gamut color:** `_OUT = RGB(17, 17, 17)`. When `pixel_fn` returns `None`, paint `_OUT`.

- [ ] **Step 1: Write failing tests**

Create `tests/picker/components/test_slicer.py`:

```python
import math
from src.picker.frame import Frame
from src.picker.colors import RGB, rgb_to_hsl, rgb_to_oklch, rgb_to_lab
from src.picker.components.slicer import (
    render_color_slicer, VIEWS, _clear_slicer_cache,
)

# Use a small frame for speed
_W, _H = 20, 10


def _frame():
    return Frame(_W, _H)


def setup_function():
    _clear_slicer_cache()


def test_render_does_not_crash():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(128, 64, 32), view_idx=0)


def test_label_appears_on_last_row():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(128, 64, 32), view_idx=0)
    # Label row is h-1 from the component row
    label_row = _H - 1
    row_text = "".join(f.get(label_row, c).char for c in range(_W))
    # RGB view 0 label should mention "R/G" and "B="
    assert "R/G" in row_text or "B=" in row_text


def test_cells_have_half_block_char():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(200, 100, 50), view_idx=0)
    # Most grid cells should contain ▀ (some corner cells might be out-of-gamut but still ▀)
    half_block_count = sum(
        1 for r in range(_H - 1) for c in range(_W)
        if f.get(r, c).char == "▀"
    )
    assert half_block_count > (_W * (_H - 1)) // 2


def test_cells_have_fg_and_bg():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="hsl", current=RGB(128, 64, 32), view_idx=0)
    # A grid cell should have both fg and bg set (both are RGB values)
    cell = f.get(0, 0)
    assert cell.fg is not None
    assert cell.bg is not None


def test_view_idx_wraps():
    f = _frame()
    # rgb has 3 views; view_idx=3 should wrap to view 0
    f2 = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(100, 100, 100), view_idx=0)
    render_color_slicer(f2, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(100, 100, 100), view_idx=3)
    # Both frames should be identical (same view)
    for r in range(_H):
        for c in range(_W):
            assert f.get(r, c) == f2.get(r, c), f"mismatch at ({r},{c})"


def test_all_models_render():
    for model in ("rgb", "hsl", "oklch", "lab"):
        f = _frame()
        render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                            model=model, current=RGB(100, 150, 200), view_idx=0)
        # Must paint at least one non-default cell
        non_default = sum(
            1 for r in range(_H) for c in range(_W)
            if f.get(r, c).char != " "
        )
        assert non_default > 0, f"model {model!r} painted nothing"


def test_cursor_marker_present():
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(128, 0, 0), view_idx=0)
    # ◆ should appear somewhere in the slicer area (rows 0..h-2)
    marker_found = any(
        f.get(r, c).char == "◆"
        for r in range(_H - 1)
        for c in range(_W)
    )
    assert marker_found


def test_oklch_view_count():
    assert len(VIEWS["oklch"]) == 4


def test_hsl_view_count():
    assert len(VIEWS["hsl"]) == 4


def test_rgb_view_count():
    assert len(VIEWS["rgb"]) == 3


def test_lab_view_count():
    assert len(VIEWS["lab"]) == 4


def test_row_col_offset():
    f = Frame(30, 15)
    render_color_slicer(f, row=2, col=5, w=20, h=10,
                        model="rgb", current=RGB(100, 100, 100), view_idx=0)
    # Row 0, col 0 should be untouched
    assert f.get(0, 0).char == " "
    # Row 2, col 5 should be painted
    assert f.get(2, 5).char == "▀"
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/pytest tests/picker/components/test_slicer.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.components.slicer'`.

- [ ] **Step 3: Implement `src/picker/components/slicer.py`** (base rendering, no cache yet)

Create `src/picker/components/slicer.py`:

```python
from __future__ import annotations
import math
from typing import Callable, List, NamedTuple, Optional, Tuple

from src.picker.frame import Frame
from src.picker.colors import (
    RGB, HSL, OKLCH, Lab,
    rgb_to_hex, hex_to_rgb,
    rgb_to_hsl, hsl_to_rgb,
    rgb_to_oklch, oklch_to_rgb,
    rgb_to_lab, lab_to_rgb,
)

_OUT = RGB(17, 17, 17)  # #111111 — out-of-gamut / out-of-circle fill color

# Module-level cache: populated in Task 7.
_SLICER_CACHE: dict[tuple, list[list[tuple[RGB, RGB]]]] = {}


def _clear_slicer_cache() -> None:
    """Empty the slicer pixel cache. Call in test teardown."""
    _SLICER_CACHE.clear()


def _luma(rgb: RGB) -> float:
    return 0.299 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _contrast(rgb: RGB) -> RGB:
    return RGB(0, 0, 0) if _luma(rgb) > 128 else RGB(255, 255, 255)


def _polar(xn: float, yn: float) -> Tuple[float, float, bool]:
    """Convert normalized (xn, yn) to polar (r, theta, inside_circle).

    Origin is at the center of the unit square. yn=1 is visual top.
    r is in [0, 1] where 1 = edge of the inscribed circle.
    """
    dx = xn - 0.5
    dy = yn - 0.5  # positive y = upward (yn=1 is top)
    r = math.sqrt(dx * dx + dy * dy) / 0.5
    theta = math.atan2(dy, dx)
    return r, theta, r <= 1.0


def _polar_cursor(theta_rad: float, r: float) -> Tuple[float, float]:
    """Convert polar back to normalized (cxn, cyn). r is in [0,1] relative to circle radius."""
    return (
        0.5 + r * 0.5 * math.cos(theta_rad),
        0.5 - r * 0.5 * math.sin(theta_rad),  # yn: positive = upward
    )


# ---------------------------------------------------------------------------
# SlicerView definition
# ---------------------------------------------------------------------------

class SlicerView(NamedTuple):
    label: str  # short label shown below the slicer, e.g. "R/G  B=32"
    pixel_fn: Callable[[float, float], Optional[RGB]]  # (xn, yn) -> RGB or None
    cursor: Tuple[float, float]  # (cxn, cyn) — 0-indexed normalized cursor position


def _make_views(
    current: RGB,
    hsl: HSL,
    oklch: OKLCH,
    lab: Lab,
) -> dict[str, list[SlicerView]]:
    """Build the view list for every model given the current color values."""

    rgb = current

    return {
        "rgb": [
            SlicerView(
                label=f"R/G  B={rgb.b}",
                pixel_fn=lambda xn, yn: RGB(round(xn * 255), round(yn * 255), rgb.b),
                cursor=(rgb.r / 255, 1.0 - rgb.g / 255),
            ),
            SlicerView(
                label=f"R/B  G={rgb.g}",
                pixel_fn=lambda xn, yn: RGB(round(xn * 255), rgb.g, round(yn * 255)),
                cursor=(rgb.r / 255, 1.0 - rgb.b / 255),
            ),
            SlicerView(
                label=f"G/B  R={rgb.r}",
                pixel_fn=lambda xn, yn: RGB(rgb.r, round(xn * 255), round(yn * 255)),
                cursor=(rgb.g / 255, 1.0 - rgb.b / 255),
            ),
        ],
        "hsl": [
            SlicerView(
                label=f"H/S  L={round(hsl.l)}",
                pixel_fn=lambda xn, yn: hsl_to_rgb(HSL(xn * 360, yn * 100, hsl.l)),
                cursor=(hsl.h / 360, 1.0 - hsl.s / 100),
            ),
            SlicerView(
                label=f"H/L  S={round(hsl.s)}",
                pixel_fn=lambda xn, yn: hsl_to_rgb(HSL(xn * 360, hsl.s, yn * 100)),
                cursor=(hsl.h / 360, 1.0 - hsl.l / 100),
            ),
            SlicerView(
                label=f"S/L  H={round(hsl.h)}°",
                pixel_fn=lambda xn, yn: hsl_to_rgb(HSL(hsl.h, xn * 100, yn * 100)),
                cursor=(hsl.s / 100, 1.0 - hsl.l / 100),
            ),
            SlicerView(
                label=f"wheel  L={round(hsl.l)}",
                pixel_fn=lambda xn, yn: (
                    (lambda r, theta, inside:
                        hsl_to_rgb(HSL(
                            (math.degrees(theta) + 360) % 360,
                            r * 100,
                            hsl.l,
                        )) if inside else None
                    )(*_polar(xn, yn))
                ),
                cursor=_polar_cursor(math.radians(hsl.h), hsl.s / 100),
            ),
        ],
        "oklch": [
            SlicerView(
                label=f"H/C  L={oklch.l}",
                pixel_fn=lambda xn, yn: oklch_to_rgb(OKLCH(oklch.l, round(yn * 400), round(xn * 360))),
                cursor=(oklch.h / 360, 1.0 - oklch.c / 400),
            ),
            SlicerView(
                label=f"H/L  C={oklch.c}",
                pixel_fn=lambda xn, yn: oklch_to_rgb(OKLCH(round(yn * 100), oklch.c, round(xn * 360))),
                cursor=(oklch.h / 360, 1.0 - oklch.l / 100),
            ),
            SlicerView(
                label=f"C/L  H={oklch.h}°",
                pixel_fn=lambda xn, yn: oklch_to_rgb(OKLCH(round(yn * 100), round(xn * 400), oklch.h)),
                cursor=(oklch.c / 400, 1.0 - oklch.l / 100),
            ),
            SlicerView(
                label=f"wheel  L={oklch.l}",
                pixel_fn=lambda xn, yn: (
                    (lambda r, theta, inside:
                        oklch_to_rgb(OKLCH(
                            oklch.l,
                            round(r * 400),
                            round((math.degrees(theta) + 360) % 360),
                        )) if inside else None
                    )(*_polar(xn, yn))
                ),
                cursor=_polar_cursor(math.radians(oklch.h), oklch.c / 400),
            ),
        ],
        "lab": [
            SlicerView(
                label=f"a/b  L={lab.l}",
                pixel_fn=lambda xn, yn: lab_to_rgb(Lab(lab.l, round(xn * 255 - 128), round(yn * 255 - 128))),
                cursor=((lab.a + 128) / 255, 1.0 - (lab.b + 128) / 255),
            ),
            SlicerView(
                label=f"L/a  b={lab.b}",
                pixel_fn=lambda xn, yn: lab_to_rgb(Lab(round(xn * 100), round(yn * 255 - 128), lab.b)),
                cursor=(lab.l / 100, 1.0 - (lab.a + 128) / 255),
            ),
            SlicerView(
                label=f"L/b  a={lab.a}",
                pixel_fn=lambda xn, yn: lab_to_rgb(Lab(round(xn * 100), lab.a, round(yn * 255 - 128))),
                cursor=(lab.l / 100, 1.0 - (lab.b + 128) / 255),
            ),
            SlicerView(
                label=f"wheel  L={lab.l}",
                pixel_fn=lambda xn, yn: (
                    (lambda r, theta, inside:
                        lab_to_rgb(Lab(
                            lab.l,
                            round(math.cos(theta) * r * 128),
                            round(math.sin(theta) * r * 128),
                        )) if inside else None
                    )(*_polar(xn, yn))
                ),
                cursor=_polar_cursor(
                    math.atan2(lab.b, lab.a),
                    math.sqrt(lab.a * lab.a + lab.b * lab.b) / 128,
                ),
            ),
        ],
    }


# Expose VIEWS as a module-level constant so tests can inspect view counts.
# Built once at module load with a reference color; used only for len() queries.
# Per-render views are constructed fresh via _make_views(current, ...) each call.
_REF = RGB(128, 128, 128)
VIEWS: dict[str, list[SlicerView]] = _make_views(
    _REF, rgb_to_hsl(_REF), rgb_to_oklch(_REF), rgb_to_lab(_REF)
)


def _compute_pixel_grid(
    view: SlicerView,
    pixel_w: int,
    pixel_h: int,
) -> list[list[RGB]]:
    """Compute the full pixel_h x pixel_w grid of RGB values for `view`.

    Each entry is the color for that logical pixel. Out-of-gamut pixels
    (where pixel_fn returns None) use _OUT.
    """
    grid: list[list[RGB]] = []
    for py in range(pixel_h):
        row_pixels: list[RGB] = []
        yn = 1.0 - py / (pixel_h - 1) if pixel_h > 1 else 1.0
        for px in range(pixel_w):
            xn = px / (pixel_w - 1) if pixel_w > 1 else 0.0
            result = view.pixel_fn(xn, yn)
            row_pixels.append(result if result is not None else _OUT)
        grid.append(row_pixels)
    return grid


def _pair_rows(grid: list[list[RGB]]) -> list[list[tuple[RGB, RGB]]]:
    """Pair consecutive pixel rows into (top_rgb, bottom_rgb) tuples.

    Each pair becomes one terminal row of half-block cells.
    If the pixel grid has an odd number of rows, the last row is paired
    with _OUT as its bottom pixel.
    """
    paired: list[list[tuple[RGB, RGB]]] = []
    i = 0
    while i < len(grid):
        top_row = grid[i]
        bot_row = grid[i + 1] if (i + 1) < len(grid) else [_OUT] * len(top_row)
        paired.append(list(zip(top_row, bot_row)))
        i += 2
    return paired


def render_color_slicer(
    frame: Frame,
    row: int,
    col: int,
    w: int,
    h: int,
    *,
    model: str,
    current: RGB,
    view_idx: int,
) -> None:
    """Paint a 2D color-space slice into `frame` at (row, col, w, h).

    Uses half-block characters (▀ U+2580): fg = top pixel, bg = bottom pixel.
    This doubles the effective vertical resolution — a component with h terminal
    rows shows h*2-2 logical pixel rows (h-1 terminal rows for pixels, 1 for label).

    The pixel grid is memoized in _SLICER_CACHE by (model, hex, view_idx, w, h).
    """
    hsl = rgb_to_hsl(current)
    oklch = rgb_to_oklch(current)
    lab = rgb_to_lab(current)

    all_views = _make_views(current, hsl, oklch, lab)
    view_list = all_views[model]
    view = view_list[view_idx % len(view_list)]

    pixel_w = max(1, w)
    grid_term_rows = max(1, h - 2)  # -1 for label row, -1 for top margin row
    pixel_h = grid_term_rows * 2    # two logical pixels per terminal row

    # Compute the pixel grid (memoized in Task 7; bare computation here)
    pixel_grid = _compute_pixel_grid(view, pixel_w, pixel_h)
    pairs = _pair_rows(pixel_grid)

    # Cursor position in pixel coordinates
    cxn, cyn = view.cursor
    cxn = max(0.0, min(1.0, cxn))
    cyn = max(0.0, min(1.0, cyn))
    cx = round(cxn * (pixel_w - 1)) if pixel_w > 1 else 0
    # cyn=1.0 is the top of the pixel grid (py=0), cyn=0.0 is py=pixel_h-1
    cy = round((1.0 - cyn) * (pixel_h - 1)) if pixel_h > 1 else 0
    cursor_term_row = cy // 2
    cursor_is_top = (cy % 2 == 0)

    # Paint one blank row at the top (row+0) as a margin
    frame.fill(row, col, w, 1, " ")

    # Paint half-block rows (start at row+1)
    for tr, pair_row in enumerate(pairs):
        abs_r = row + 1 + tr
        for pc, (top_rgb, bot_rgb) in enumerate(pair_row):
            is_cursor = (pc == cx and tr == cursor_term_row)
            if is_cursor:
                # Cursor ◆: draw in the appropriate half (top or bottom)
                if cursor_is_top:
                    marker_color = _contrast(top_rgb)
                    frame.put_cell(abs_r, col + pc, "◆",
                                   fg=marker_color, bg=bot_rgb)
                else:
                    marker_color = _contrast(bot_rgb)
                    # ◆ always goes in fg (upper half); swap top and bottom
                    # to keep the cursor in the bottom half visually
                    frame.put_cell(abs_r, col + pc, "▄",
                                   fg=marker_color, bg=top_rgb)
            else:
                frame.put_cell(abs_r, col + pc, "▀", fg=top_rgb, bg=bot_rgb)

    # Label row
    label_row = row + h - 1
    frame.fill(label_row, col, w, 1, " ")
    frame.put_str(label_row, col + 1, view.label, fg=RGB(128, 128, 128))
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/components/test_slicer.py -v
```

Expected: 12 passed. (The `test_cursor_marker_present` test may use `◆` or `▄` depending on which half the cursor falls in — check that either marker appears within the slicer bounds.)

- [ ] **Step 5: Commit**

```bash
git add src/picker/components/slicer.py tests/picker/components/test_slicer.py
git commit -m "feat(picker): render_color_slicer base rendering with half-block pixels"
```

---

## Task 7: ColorSlicer — memoization

**Files:**
- Modify: `src/picker/components/slicer.py`
- Modify: `tests/picker/components/test_slicer.py`

### Design notes

The pixel grid computation (`_compute_pixel_grid`) is expensive: for a 40×20 slicer, it calls `pixel_fn` 1600 times per frame. In practice the grid only changes when `(model, current_hex, view_idx, w, h)` changes. We memoize the `list[list[tuple[RGB, RGB]]]` (paired rows) in `_SLICER_CACHE`, a module-level dict.

Cache key: `(model, rgb_to_hex(current), view_idx % len(view_list), pixel_w, pixel_h)`.

The cache is intentionally unbounded: the app renders a handful of distinct sizes and a handful of distinct colors — the working set is tiny. `_clear_slicer_cache()` exists for tests.

To test that memoization works, we use a call counter embedded in a mutable container (a `list[int]`) that is closed over by a patched `pixel_fn`. The plan avoids `unittest.mock` (stdlib-only) by using a simple counter dict.

- [ ] **Step 1: Add memoization tests**

Append to `tests/picker/components/test_slicer.py`:

```python
from src.picker.components.slicer import _SLICER_CACHE


def test_cache_populated_after_first_render():
    _clear_slicer_cache()
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(10, 20, 30), view_idx=0)
    assert len(_SLICER_CACHE) == 1


def test_second_render_same_args_hits_cache():
    """The pixel computation must run exactly once for two identical renders."""
    _clear_slicer_cache()

    call_count = [0]
    _orig_compute = __import__(
        "src.picker.components.slicer", fromlist=["_compute_pixel_grid"]
    )._compute_pixel_grid

    # Patch _compute_pixel_grid with a counting wrapper
    import src.picker.components.slicer as slicer_mod

    def counting_compute(view, pw, ph):
        call_count[0] += 1
        return _orig_compute(view, pw, ph)

    slicer_mod._compute_pixel_grid = counting_compute
    try:
        f = _frame()
        render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                            model="rgb", current=RGB(50, 100, 150), view_idx=1)
        render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                            model="rgb", current=RGB(50, 100, 150), view_idx=1)
        assert call_count[0] == 1, (
            f"_compute_pixel_grid called {call_count[0]} times; expected 1 (cached on second call)"
        )
    finally:
        slicer_mod._compute_pixel_grid = _orig_compute


def test_different_args_miss_cache():
    _clear_slicer_cache()
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(10, 20, 30), view_idx=0)
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="rgb", current=RGB(40, 50, 60), view_idx=0)
    # Different current colors -> two distinct cache entries
    assert len(_SLICER_CACHE) == 2


def test_cache_is_cleared_by_helper():
    _clear_slicer_cache()
    f = _frame()
    render_color_slicer(f, row=0, col=0, w=_W, h=_H,
                        model="hsl", current=RGB(1, 2, 3), view_idx=0)
    assert len(_SLICER_CACHE) >= 1
    _clear_slicer_cache()
    assert len(_SLICER_CACHE) == 0
```

- [ ] **Step 2: Run new tests, expect failure**

```bash
.venv/bin/pytest tests/picker/components/test_slicer.py -v -k "cache"
```

Expected: `test_cache_populated_after_first_render` fails because the cache is never filled (cache logic not yet wired into `render_color_slicer`).

- [ ] **Step 3: Wire memoization into `render_color_slicer`**

In `src/picker/components/slicer.py`, replace the block that currently reads:

```python
    # Compute the pixel grid (memoized in Task 7; bare computation here)
    pixel_grid = _compute_pixel_grid(view, pixel_w, pixel_h)
    pairs = _pair_rows(pixel_grid)
```

with:

```python
    # Memoized pixel grid computation.
    # Key encodes everything that changes the visual output of the grid.
    cache_key = (model, rgb_to_hex(current), view_idx % len(view_list), pixel_w, pixel_h)
    if cache_key not in _SLICER_CACHE:
        pixel_grid = _compute_pixel_grid(view, pixel_w, pixel_h)
        _SLICER_CACHE[cache_key] = _pair_rows(pixel_grid)
    pairs = _SLICER_CACHE[cache_key]
```

- [ ] **Step 4: Run all slicer tests, expect pass**

```bash
.venv/bin/pytest tests/picker/components/test_slicer.py -v
```

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/components/slicer.py tests/picker/components/test_slicer.py
git commit -m "feat(picker): slicer pixel-grid memoization"
```

---

## Task 8: End-of-phase verification + push branch

**Files:**
- No new files.

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass. Count should be the Phase 2 total (71) plus the new component tests (approximately 9 + 9 + 10 + 10 + 16 = 54), totaling approximately 125 tests. Exact count may vary if edge-case tests were added. Zero failures, zero errors.

- [ ] **Step 2: Verify no runtime imports outside stdlib and `src.picker`**

```bash
grep -r "^import\|^from" src/picker/components/ | grep -v "^Binary" | grep -Ev "(^src/picker|from __future__|from src\.picker|import math|import typing|import sys|import os|import re)"
```

Expected: no output. All imports in the components subpackage should be from Python stdlib or from `src.picker.*`.

- [ ] **Step 3: Verify no `print()` calls in library code**

```bash
grep -rn "print(" src/picker/components/
```

Expected: no output.

- [ ] **Step 4: Verify no inline `style=` attributes**

Not applicable (Python, not JSX). Skip.

- [ ] **Step 5: Quick import smoke test**

```bash
.venv/bin/python -c "
from src.picker.components.slider import render_slider
from src.picker.components.settings import render_settings
from src.picker.components.preview import render_terminal_preview
from src.picker.components.swatch_browser import render_swatch_browser, sort_entries
from src.picker.components.slicer import render_color_slicer, VIEWS, _clear_slicer_cache
print('all components importable OK')
print('VIEWS keys:', list(VIEWS.keys()))
print('rgb view count:', len(VIEWS['rgb']))
"
```

Expected output:
```
all components importable OK
VIEWS keys: ['rgb', 'hsl', 'oklch', 'lab']
rgb view count: 3
```

- [ ] **Step 6: Push branch**

```bash
git push -u origin feature/picker-components
```

---

## Verification before declaring Phase 3 done

Run this checklist manually before opening a PR:

- [ ] `.venv/bin/pytest -v` — all green, zero failures.
- [ ] `grep -rn "TBD\|TODO\|placeholder\|NotImplemented" src/picker/components/` — no output.
- [ ] `grep -rn "print(" src/picker/components/` — no output.
- [ ] Each component can be imported independently without side effects.
- [ ] `_clear_slicer_cache()` is called in test `setup_function` so slicer tests are isolated.
- [ ] `git diff main..HEAD --stat` lists only files under `src/picker/components/` and `tests/picker/components/`, plus `src/picker/components/__init__.py` and `tests/picker/components/__init__.py`.

## What comes next (NOT in this plan)

- **Phase 4:** `App` state (a single dict holding `model`, `step`, `live`, `bg_rgb`, `fg_rgb`, `view_idx`, `focused_panel`, `filter_str`, `sort_mode`, `focused_swatch_idx`), pure `update(state, key_event) -> state` function, pure `render_app(state, cols, rows) -> Frame` that composes all five components into a single Frame, main event loop wiring the key reader to update+render+flush.
- **Phase 5:** `bin/hued-pick` shim replacement, `bin/hued -i` wiring, Homebrew formula update, README docs, removal of Node-based picker artifacts.
