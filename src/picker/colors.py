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
