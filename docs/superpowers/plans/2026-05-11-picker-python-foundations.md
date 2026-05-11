# Picker Python Port — Phase 1: Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stdlib-only Python foundation for the interactive picker — color-space math, named-color data, raw-mode terminal control, key parsing, and ANSI/OSC emit helpers — fully unit-tested, with a smoke-test program that exercises everything end-to-end.

**Architecture:** Plain modules in `src/picker/`, one responsibility per file. No third-party deps at runtime; `pytest` for tests only. Elm/MVU style (pure `update`/`render`) will come in Phase 2; this phase only ships building blocks.

**Tech Stack:** Python 3.9+ (stdlib `tty`, `termios`, `sys`, `signal`, `os`, `shutil`, `math`, `dataclasses`, `re`). Dev: `pytest`.

**Scope:** This is the first of several plans for the picker port. Phase 1 produces an importable Python package and a smoke-test binary; it does NOT yet replace `bin/hued-pick`. Subsequent phases (render engine, components, app, packaging) get their own plans.

**Branch strategy:** Work on a new branch `feature/picker-python` cut from `main`. The existing TS picker on `feature/interactive-mode` stays as a visual reference and is not merged.

---

## File Structure

Files this plan creates or modifies:

- **Create:** `src/picker/__init__.py` — empty, marks the package.
- **Create:** `src/picker/colors.py` — RGB dataclass, hex parsing, RGB↔HSL/OKLCH/Lab conversions, `nearest_name()`.
- **Create:** `src/picker/names.py` — `NAMED_COLORS: dict[str, str]` (name → hex), generated once from the existing TS source.
- **Create:** `src/picker/term.py` — raw-mode context manager, key reader, OSC/ANSI emit helpers, terminal size + SIGWINCH.
- **Create:** `src/picker/keys.py` — `Key` enum + `KeyEvent` dataclass returned by the key reader.
- **Create:** `src/picker/__main__.py` — smoke-test program: alt-screen, draw swatches, read a key, exit cleanly.
- **Create:** `tests/picker/__init__.py` — empty.
- **Create:** `tests/picker/test_colors.py` — round-trip and edge-case tests for color math.
- **Create:** `tests/picker/test_names.py` — sanity checks on the name list.
- **Create:** `tests/picker/test_keys.py` — key-parser tests using fed-in byte sequences.
- **Create:** `requirements-dev.txt` — `pytest`.
- **Create:** `pytest.ini` — sets `pythonpath = .` so `from src.picker.* import ...` resolves when running tests from repo root.
- **Create:** `scripts/names_to_py.py` — one-shot generator (TS → Python data file).
- **Modify:** `.gitignore` — add `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `.venv/`.

---

## Task 1: Branch + project scaffold

**Files:**
- Create: `src/picker/__init__.py`
- Create: `tests/picker/__init__.py`
- Create: `requirements-dev.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Create branch from main**

```bash
git checkout main && git pull --ff-only
git checkout -b feature/picker-python
```

- [ ] **Step 2: Create empty package files**

```bash
mkdir -p src/picker tests/picker
touch src/picker/__init__.py tests/picker/__init__.py
```

- [ ] **Step 3: Add dev requirements**

Create `requirements-dev.txt`:

```
pytest>=7.0
```

- [ ] **Step 4: Configure pytest**

Create `pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

This makes `from src.picker.* import ...` work when pytest is invoked from the repo root.

- [ ] **Step 5: Extend .gitignore**

Append to `.gitignore`:

```
__pycache__/
.pytest_cache/
*.egg-info/
.venv/
```

- [ ] **Step 6: Verify pytest discovers nothing yet**

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -v
```

Expected: `no tests ran in ...`. Confirms test discovery works.

- [ ] **Step 7: Commit**

```bash
git add src/picker/__init__.py tests/picker/__init__.py requirements-dev.txt pytest.ini .gitignore
git commit -m "chore: scaffold src/picker Python package and dev deps"
```

---

## Task 2: RGB dataclass + hex parsing

**Files:**
- Create: `src/picker/colors.py`
- Create: `tests/picker/test_colors.py`

- [ ] **Step 1: Write failing tests for hex_to_rgb and rgb_to_hex**

Create `tests/picker/test_colors.py`:

```python
from src.picker.colors import RGB, hex_to_rgb, rgb_to_hex


def test_hex_to_rgb_six_digit():
    assert hex_to_rgb("#1a0a0a") == RGB(0x1a, 0x0a, 0x0a)


def test_hex_to_rgb_three_digit_expands():
    assert hex_to_rgb("#f00") == RGB(255, 0, 0)


def test_hex_to_rgb_no_leading_hash():
    assert hex_to_rgb("00ff00") == RGB(0, 255, 0)


def test_hex_to_rgb_uppercase():
    assert hex_to_rgb("#FFAA88") == RGB(255, 170, 136)


def test_rgb_to_hex_pads_zeros():
    assert rgb_to_hex(RGB(1, 2, 3)) == "#010203"


def test_rgb_to_hex_full_range():
    assert rgb_to_hex(RGB(255, 0, 128)) == "#ff0080"


def test_rgb_hex_roundtrip():
    for r in (0, 17, 128, 255):
        for g in (0, 17, 128, 255):
            for b in (0, 17, 128, 255):
                rgb = RGB(r, g, b)
                assert hex_to_rgb(rgb_to_hex(rgb)) == rgb
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.picker.colors'`.

- [ ] **Step 3: Implement RGB + hex helpers**

Create `src/picker/colors.py`:

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RGB:
    r: int
    g: int
    b: int


def hex_to_rgb(value: str) -> RGB:
    bare = value[1:] if value.startswith("#") else value
    if len(bare) == 3:
        bare = "".join(c + c for c in bare)
    n = int(bare, 16)
    return RGB((n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff)


def rgb_to_hex(rgb: RGB) -> str:
    return f"#{rgb.r:02x}{rgb.g:02x}{rgb.b:02x}"
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/colors.py tests/picker/test_colors.py
git commit -m "feat(picker): RGB dataclass and hex parsing"
```

---

## Task 3: RGB ↔ HSL

**Files:**
- Modify: `src/picker/colors.py`
- Modify: `tests/picker/test_colors.py`

- [ ] **Step 1: Add failing HSL tests**

Append to `tests/picker/test_colors.py`:

```python
from src.picker.colors import HSL, rgb_to_hsl, hsl_to_rgb


def test_rgb_to_hsl_black():
    h = rgb_to_hsl(RGB(0, 0, 0))
    assert h.l == 0 and h.s == 0


def test_rgb_to_hsl_white():
    h = rgb_to_hsl(RGB(255, 255, 255))
    assert h.l == 100 and h.s == 0


def test_rgb_to_hsl_pure_red():
    h = rgb_to_hsl(RGB(255, 0, 0))
    assert round(h.h) == 0 and round(h.s) == 100 and round(h.l) == 50


def test_hsl_roundtrip_primaries():
    for rgb in (RGB(255, 0, 0), RGB(0, 255, 0), RGB(0, 0, 255),
                RGB(255, 255, 0), RGB(0, 255, 255), RGB(255, 0, 255)):
        back = hsl_to_rgb(rgb_to_hsl(rgb))
        assert back == rgb
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: `ImportError: cannot import name 'HSL'`.

- [ ] **Step 3: Implement HSL conversions**

Append to `src/picker/colors.py`:

```python
@dataclass(frozen=True)
class HSL:
    h: float  # 0-360
    s: float  # 0-100
    l: float  # 0-100


def rgb_to_hsl(rgb: RGB) -> HSL:
    rn, gn, bn = rgb.r / 255, rgb.g / 255, rgb.b / 255
    mx, mn = max(rn, gn, bn), min(rn, gn, bn)
    l = (mx + mn) / 2
    if mx == mn:
        return HSL(0.0, 0.0, l * 100)
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == rn:
        h = ((gn - bn) / d + (6 if gn < bn else 0)) / 6
    elif mx == gn:
        h = ((bn - rn) / d + 2) / 6
    else:
        h = ((rn - gn) / d + 4) / 6
    return HSL(h * 360, s * 100, l * 100)


def hsl_to_rgb(hsl: HSL) -> RGB:
    sn, ln = hsl.s / 100, hsl.l / 100
    if sn == 0:
        v = round(ln * 255)
        return RGB(v, v, v)
    q = ln * (1 + sn) if ln < 0.5 else ln + sn - ln * sn
    p = 2 * ln - q

    def hue2rgb(t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    hn = hsl.h / 360
    return RGB(
        round(hue2rgb(hn + 1 / 3) * 255),
        round(hue2rgb(hn) * 255),
        round(hue2rgb(hn - 1 / 3) * 255),
    )
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/colors.py tests/picker/test_colors.py
git commit -m "feat(picker): RGB <-> HSL conversion"
```

---

## Task 4: RGB ↔ OKLCH

**Files:**
- Modify: `src/picker/colors.py`
- Modify: `tests/picker/test_colors.py`

- [ ] **Step 1: Add failing OKLCH tests**

Append to `tests/picker/test_colors.py`:

```python
from src.picker.colors import OKLCH, rgb_to_oklch, oklch_to_rgb


def test_rgb_to_oklch_black():
    o = rgb_to_oklch(RGB(0, 0, 0))
    assert o.l == 0 and o.c == 0


def test_rgb_to_oklch_white():
    o = rgb_to_oklch(RGB(255, 255, 255))
    assert o.l == 100 and o.c < 5  # near-zero chroma


def test_oklch_roundtrip_tolerance():
    # Prototype-grade tolerance: each channel within 2 of original
    for rgb in (RGB(64, 128, 192), RGB(200, 50, 100), RGB(20, 200, 80)):
        back = oklch_to_rgb(rgb_to_oklch(rgb))
        assert abs(back.r - rgb.r) <= 2
        assert abs(back.g - rgb.g) <= 2
        assert abs(back.b - rgb.b) <= 2
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v -k oklch
```

Expected: `ImportError: cannot import name 'OKLCH'`.

- [ ] **Step 3: Implement OKLCH conversions**

Append to `src/picker/colors.py`:

```python
import math


@dataclass(frozen=True)
class OKLCH:
    l: int  # 0-100
    c: int  # 0-400 (raw_c * 1000, rounded)
    h: int  # 0-360


def _linearize(v: int) -> float:
    s = v / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def _delinearize(v: float) -> float:
    return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055


def _clamp_u8(x: float) -> int:
    return max(0, min(255, round(x)))


def rgb_to_oklch(rgb: RGB) -> OKLCH:
    rl, gl, bl = _linearize(rgb.r), _linearize(rgb.g), _linearize(rgb.b)
    l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl
    l_, m_, s_ = l ** (1 / 3) if l >= 0 else -((-l) ** (1 / 3)), \
                 m ** (1 / 3) if m >= 0 else -((-m) ** (1 / 3)), \
                 s ** (1 / 3) if s >= 0 else -((-s) ** (1 / 3))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bk = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.sqrt(a * a + bk * bk)
    H = math.degrees(math.atan2(bk, a))
    if H < 0:
        H += 360
    return OKLCH(round(L * 100), round(C * 1000), round(H))


def oklch_to_rgb(oklch: OKLCH) -> RGB:
    L = oklch.l / 100
    C = oklch.c / 1000
    H = oklch.h
    a = C * math.cos(math.radians(H))
    bk = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * bk
    m_ = L - 0.1055613458 * a - 0.0638541728 * bk
    s_ = L - 0.0894841775 * a - 1.2914855480 * bk
    l_c, m_c, s_c = l_ ** 3, m_ ** 3, s_ ** 3
    rl = +4.0767416621 * l_c - 3.3077115913 * m_c + 0.2309699292 * s_c
    gl = -1.2684380046 * l_c + 2.6097574011 * m_c - 0.3413193965 * s_c
    bl = -0.0041960863 * l_c - 0.7034186147 * m_c + 1.7076147010 * s_c
    return RGB(
        _clamp_u8(_delinearize(rl) * 255),
        _clamp_u8(_delinearize(gl) * 255),
        _clamp_u8(_delinearize(bl) * 255),
    )
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/colors.py tests/picker/test_colors.py
git commit -m "feat(picker): RGB <-> OKLCH conversion"
```

---

## Task 5: RGB ↔ Lab

**Files:**
- Modify: `src/picker/colors.py`
- Modify: `tests/picker/test_colors.py`

- [ ] **Step 1: Add failing Lab tests**

Append to `tests/picker/test_colors.py`:

```python
from src.picker.colors import Lab, rgb_to_lab, lab_to_rgb


def test_rgb_to_lab_black():
    lab = rgb_to_lab(RGB(0, 0, 0))
    assert lab.l == 0


def test_rgb_to_lab_white():
    lab = rgb_to_lab(RGB(255, 255, 255))
    assert lab.l == 100 and abs(lab.a) <= 1 and abs(lab.b) <= 1


def test_lab_roundtrip_tolerance():
    for rgb in (RGB(64, 128, 192), RGB(200, 50, 100), RGB(20, 200, 80)):
        back = lab_to_rgb(rgb_to_lab(rgb))
        assert abs(back.r - rgb.r) <= 2
        assert abs(back.g - rgb.g) <= 2
        assert abs(back.b - rgb.b) <= 2
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v -k lab
```

Expected: `ImportError: cannot import name 'Lab'`.

- [ ] **Step 3: Implement Lab conversions**

Append to `src/picker/colors.py`:

```python
@dataclass(frozen=True)
class Lab:
    l: int  # 0-100
    a: int  # -128 to 127
    b: int  # -128 to 127


def rgb_to_lab(rgb: RGB) -> Lab:
    rl, gl, bl = _linearize(rgb.r), _linearize(rgb.g), _linearize(rgb.b)
    x = (0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl) / 0.95047
    y = (0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl) / 1.00000
    z = (0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    L = 116 * f(y) - 16
    A = 500 * (f(x) - f(y))
    B = 200 * (f(y) - f(z))
    return Lab(round(L), round(A), round(B))


def lab_to_rgb(lab: Lab) -> RGB:
    fy = (lab.l + 16) / 116
    fx = lab.a / 500 + fy
    fz = fy - lab.b / 200

    def fi(t: float) -> float:
        return t ** 3 if t > 0.206897 else (t - 16 / 116) / 7.787

    x = fi(fx) * 0.95047
    y = fi(fy) * 1.00000
    z = fi(fz) * 1.08883
    rl = +3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    gl = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    bl = +0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return RGB(
        _clamp_u8(_delinearize(rl) * 255),
        _clamp_u8(_delinearize(gl) * 255),
        _clamp_u8(_delinearize(bl) * 255),
    )
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/colors.py tests/picker/test_colors.py
git commit -m "feat(picker): RGB <-> Lab conversion"
```

---

## Task 6: Nearest-name lookup

**Files:**
- Modify: `src/picker/colors.py`
- Modify: `tests/picker/test_colors.py`

- [ ] **Step 1: Add failing test**

Append to `tests/picker/test_colors.py`:

```python
from src.picker.colors import nearest_name


def test_nearest_name_exact_match():
    names = {"red": "#ff0000", "green": "#00ff00", "blue": "#0000ff"}
    assert nearest_name(RGB(255, 0, 0), names) == "red"


def test_nearest_name_close_match():
    names = {"red": "#ff0000", "green": "#00ff00", "blue": "#0000ff"}
    assert nearest_name(RGB(250, 5, 5), names) == "red"


def test_nearest_name_empty_returns_empty_string():
    assert nearest_name(RGB(128, 128, 128), {}) == ""
```

- [ ] **Step 2: Run tests, expect failure**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v -k nearest
```

Expected: `ImportError: cannot import name 'nearest_name'`.

- [ ] **Step 3: Implement**

Append to `src/picker/colors.py`:

```python
def nearest_name(rgb: RGB, names: dict[str, str]) -> str:
    best = ""
    best_dist = float("inf")
    for name, hex_val in names.items():
        c = hex_to_rgb(hex_val)
        d = (c.r - rgb.r) ** 2 + (c.g - rgb.g) ** 2 + (c.b - rgb.b) ** 2
        if d < best_dist:
            best_dist = d
            best = name
    return best
```

- [ ] **Step 4: Run tests, expect pass**

```bash
.venv/bin/pytest tests/picker/test_colors.py -v
```

Expected: 20 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/colors.py tests/picker/test_colors.py
git commit -m "feat(picker): nearest-name lookup"
```

---

## Task 7: Named-color data file

**Files:**
- Create: `scripts/names_to_py.py`
- Create: `src/picker/names.py`
- Create: `tests/picker/test_names.py`

- [ ] **Step 1: Write the one-shot generator script**

Create `scripts/names_to_py.py`:

```python
"""One-shot: parse src/picker/lib/names.ts (TS) into src/picker/names.py.

Run manually once: python3 scripts/names_to_py.py
The output file is committed; this script is not part of the build.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "picker" / "lib" / "names.ts"
DST = ROOT / "src" / "picker" / "names.py"

if not SRC.exists():
    sys.exit(f"missing {SRC} — checkout feature/interactive-mode to get it")

pattern = re.compile(r'"([a-z0-9]+)":\s*"(#[0-9a-fA-F]{6})"')
pairs = pattern.findall(SRC.read_text())
if not pairs:
    sys.exit("no entries parsed; check the TS file format")

lines = ["# Generated by scripts/names_to_py.py from src/picker/lib/names.ts",
         "# Do not edit directly.",
         "",
         "NAMED_COLORS: dict[str, str] = {"]
for name, hex_val in pairs:
    lines.append(f'    "{name}": "{hex_val.lower()}",')
lines.append("}")
lines.append("")
DST.write_text("\n".join(lines))
print(f"wrote {len(pairs)} entries to {DST}")
```

- [ ] **Step 2: Fetch the TS source from the interactive-mode branch and run the generator**

```bash
git show feature/interactive-mode:src/picker/lib/names.ts > /tmp/names.ts
mkdir -p src/picker/lib
cp /tmp/names.ts src/picker/lib/names.ts
python3 scripts/names_to_py.py
```

Expected: `wrote 163 entries to .../src/picker/names.py` (approximate count).

- [ ] **Step 3: Remove the TS file (we only need the .py output)**

```bash
rm -rf src/picker/lib
```

- [ ] **Step 4: Add sanity tests**

Create `tests/picker/test_names.py`:

```python
from src.picker.names import NAMED_COLORS


def test_named_colors_nonempty():
    assert len(NAMED_COLORS) > 100


def test_named_colors_known_entries():
    assert NAMED_COLORS["red"] == "#ff0000"
    assert NAMED_COLORS["midnightblue"] == "#191970"
    assert NAMED_COLORS["aliceblue"] == "#f0f8ff"


def test_named_colors_all_valid_hex():
    import re
    for name, hex_val in NAMED_COLORS.items():
        assert re.match(r"^#[0-9a-f]{6}$", hex_val), f"{name}={hex_val}"
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/pytest tests/picker/test_names.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/names_to_py.py src/picker/names.py tests/picker/test_names.py
git commit -m "feat(picker): named-color data + generator script"
```

---

## Task 8: Key event types

**Files:**
- Create: `src/picker/keys.py`
- Create: `tests/picker/test_keys.py`

- [ ] **Step 1: Add failing tests for the key types**

Create `tests/picker/test_keys.py`:

```python
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
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_keys.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `src/picker/keys.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class Key(Enum):
    CHAR = auto()
    ARROW_UP = auto()
    ARROW_DOWN = auto()
    ARROW_LEFT = auto()
    ARROW_RIGHT = auto()
    ENTER = auto()
    TAB = auto()
    ESC = auto()
    BACKSPACE = auto()
    DELETE = auto()
    CTRL_C = auto()
    CTRL_L = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class KeyEvent:
    key: Key
    char: Optional[str]
    shift: bool
    ctrl: bool
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_keys.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/keys.py tests/picker/test_keys.py
git commit -m "feat(picker): Key enum and KeyEvent dataclass"
```

---

## Task 9: Key parser

**Files:**
- Create: `src/picker/term.py` (parser portion only this task)
- Modify: `tests/picker/test_keys.py`

The parser is a pure function `parse_key(buf: bytes) -> KeyEvent`. The IO-bound reader that fills the buffer is built on top in Task 11.

- [ ] **Step 1: Add failing parser tests**

Append to `tests/picker/test_keys.py`:

```python
from src.picker.term import parse_key


def test_parse_plain_char():
    e = parse_key(b"a")
    assert e.key is Key.CHAR and e.char == "a" and not e.shift and not e.ctrl


def test_parse_uppercase_char():
    e = parse_key(b"A")
    assert e.key is Key.CHAR and e.char == "A"


def test_parse_ctrl_c():
    assert parse_key(b"\x03").key is Key.CTRL_C


def test_parse_ctrl_l():
    assert parse_key(b"\x0c").key is Key.CTRL_L


def test_parse_enter_cr():
    assert parse_key(b"\r").key is Key.ENTER


def test_parse_enter_lf():
    assert parse_key(b"\n").key is Key.ENTER


def test_parse_tab():
    assert parse_key(b"\t").key is Key.TAB


def test_parse_backspace_del():
    assert parse_key(b"\x7f").key is Key.BACKSPACE


def test_parse_lone_esc():
    assert parse_key(b"\x1b").key is Key.ESC


def test_parse_arrow_up():
    assert parse_key(b"\x1b[A").key is Key.ARROW_UP


def test_parse_arrow_down():
    assert parse_key(b"\x1b[B").key is Key.ARROW_DOWN


def test_parse_arrow_right():
    assert parse_key(b"\x1b[C").key is Key.ARROW_RIGHT


def test_parse_arrow_left():
    assert parse_key(b"\x1b[D").key is Key.ARROW_LEFT


def test_parse_shift_arrow_left():
    # CSI 1;2 D — modifier 2 = shift
    e = parse_key(b"\x1b[1;2D")
    assert e.key is Key.ARROW_LEFT and e.shift


def test_parse_unknown_csi_returns_unknown():
    assert parse_key(b"\x1b[99~").key is Key.UNKNOWN
```

- [ ] **Step 2: Run, expect failure**

```bash
.venv/bin/pytest tests/picker/test_keys.py -v -k parse
```

Expected: `ImportError`.

- [ ] **Step 3: Implement parser in term.py**

Create `src/picker/term.py`:

```python
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
```

- [ ] **Step 4: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_keys.py -v
```

Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add src/picker/term.py tests/picker/test_keys.py
git commit -m "feat(picker): pure key-byte parser"
```

---

## Task 10: ANSI/OSC emit helpers

**Files:**
- Modify: `src/picker/term.py`

These are write-side helpers that emit escape sequences to a stream. No tests — they're trivial string builders and verified by the smoke test in Task 12.

- [ ] **Step 1: Add emit helpers to term.py**

Append to `src/picker/term.py`:

```python
import sys
from typing import IO


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
```

- [ ] **Step 2: Sanity test the string-builder helpers**

Create `tests/picker/test_term.py`:

```python
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
```

- [ ] **Step 3: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_term.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
git add src/picker/term.py tests/picker/test_term.py
git commit -m "feat(picker): ANSI and OSC emit helpers"
```

---

## Task 11: Raw mode + key reader + size

**Files:**
- Modify: `src/picker/term.py`

The raw-mode context manager and blocking key reader can't be unit-tested cleanly (they touch real `/dev/tty`). They get exercised by the smoke test in Task 12.

- [ ] **Step 1: Add raw_mode, read_key, get_size**

Append to `src/picker/term.py`:

```python
import os
import termios
import tty
import select
import shutil
from contextlib import contextmanager
from typing import Iterator


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
```

- [ ] **Step 2: Add a test for get_size**

Append to `tests/picker/test_term.py`:

```python
from src.picker.term import get_size


def test_get_size_returns_positive_pair():
    cols, rows = get_size()
    assert cols >= 1 and rows >= 1
```

- [ ] **Step 3: Run, expect pass**

```bash
.venv/bin/pytest tests/picker/test_term.py -v
```

Expected: 6 passed.

- [ ] **Step 4: Commit**

```bash
git add src/picker/term.py tests/picker/test_term.py
git commit -m "feat(picker): raw-mode context, key reader, terminal size"
```

---

## Task 12: End-to-end smoke test

**Files:**
- Create: `src/picker/__main__.py`

This is the validation gate for Phase 1: a runnable program that exercises every module — alt-screen entry/exit, truecolor cell rendering, OSC live preview, raw-mode key reading, clean teardown.

- [ ] **Step 1: Write the smoke program**

Create `src/picker/__main__.py`:

```python
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
```

- [ ] **Step 2: Run the smoke test manually**

```bash
python3 -m src.picker
```

Expected behavior:
- Terminal flashes to a different background color (the first NAMED_COLORS entry — likely aliceblue).
- A row of 8 truecolor swatches appears at the top of the screen.
- A help line appears.
- After pressing a key, terminal returns to your normal background.
- One line prints describing the key (e.g., `got: key=ARROW_UP char=None shift=False ctrl=False`).

If any of those steps misbehave (lingering escape codes, cursor stays hidden, bg doesn't reset), debug before committing.

- [ ] **Step 3: Run all tests one more time**

```bash
.venv/bin/pytest tests/ -v
```

Expected: all tests pass (color: 20, names: 3, keys: 18, term: 6 — total 47).

- [ ] **Step 4: Commit**

```bash
git add src/picker/__main__.py
git commit -m "feat(picker): phase-1 smoke test program"
```

- [ ] **Step 5: Push branch**

```bash
git push -u origin feature/picker-python
```

---

## Verification before declaring Phase 1 done

Run this checklist manually before opening a PR:

- [ ] `.venv/bin/pytest tests/ -v` — all green.
- [ ] `python3 -m src.picker` — terminal bg changes; arrow keys, shift-arrow, plain chars, ctrl-c, enter, tab all produce sensible output; terminal restores cleanly on exit.
- [ ] In a non-color terminal (or with `TERM=dumb`), the smoke program may render wrong but must not hang or corrupt the terminal — confirm `python3 -m src.picker < /dev/null` exits cleanly (it'll read EOF as UNKNOWN, that's fine).
- [ ] No new third-party runtime deps in `src/picker/` (grep for `import` lines, all should be stdlib or `src.picker.*`).
- [ ] No `print()` calls in library code (only in `__main__.py`).

## What comes next (NOT in this plan)

- **Phase 2:** Frame buffer / render engine. A `Frame` class that lets callers paint cells and emits one minimal escape-sequence blob per flush. SIGWINCH-driven redraw.
- **Phase 3:** Components (Slider, Settings, TerminalPreview, SwatchBrowser, ColorSlicer).
- **Phase 4:** `App` state, `update()`, `render()`, main loop.
- **Phase 5:** `bin/hued-pick` shim, `bin/hued -i` wiring, Homebrew formula update, README docs, removal of Node-based picker artifacts.

Each of those will get its own plan written after this one lands.
