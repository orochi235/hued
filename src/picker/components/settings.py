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
