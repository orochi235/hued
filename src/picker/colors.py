from __future__ import annotations
from dataclasses import dataclass
import math


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
