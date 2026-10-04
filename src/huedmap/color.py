"""The color math behind the map: where a color sits, how far apart two are, what is unused.

Everything is measured in OKLab, where equal distances look about equally different.
"""
from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass


Lab = tuple[float, float, float]


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


def _linearize(v: int) -> float:
    s = v / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def _delinearize(v: float) -> float:
    return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055


def _clamp_u8(x: float) -> int:
    return max(0, min(255, round(x)))


def _cbrt(v: float) -> float:
    return v ** (1 / 3) if v >= 0 else -((-v) ** (1 / 3))


def rgb_to_oklab(rgb: RGB) -> tuple[float, float, float]:
    rl, gl, bl = _linearize(rgb.r), _linearize(rgb.g), _linearize(rgb.b)
    l_ = _cbrt(0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl)
    m_ = _cbrt(0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl)
    s_ = _cbrt(0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear(L: float, a: float, b: float) -> tuple[float, float, float]:
    """Linear sRGB, unclamped: a channel outside 0..1 means out of gamut."""
    l_c = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_c = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_c = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        +4.0767416621 * l_c - 3.3077115913 * m_c + 0.2309699292 * s_c,
        -1.2684380046 * l_c + 2.6097574011 * m_c - 0.3413193965 * s_c,
        -0.0041960863 * l_c - 0.7034186147 * m_c + 1.7076147010 * s_c,
    )


def linear_to_rgb(linear: tuple[float, float, float]) -> RGB:
    return RGB(*(_clamp_u8(_delinearize(max(0.0, v)) * 255) for v in linear))

# Chosen by eye on one palette of 46 colors, not derived.
CLOSE = 0.10
BANDS = {"any": (0.20, 0.92), "dark": (0.20, 0.50), "light": (0.60, 0.92)}

GRAY_CHROMA = 0.03
MIN_GAP_CHROMA = 0.05
LIGHT = 0.6
FIELD_CHROMA = 0.9
GRID_STEP = 15


def lab(hexv: str) -> Lab:
    return rgb_to_oklab(hex_to_rgb(hexv))


def distance(a: Lab, b: Lab) -> float:
    return math.dist(a, b)


def contrast(a: str, b: str) -> float:
    """The WCAG contrast ratio between two colors, 1 to 21."""
    def luminance(hexv: str) -> float:
        rgb = hex_to_rgb(hexv)
        return 0.2126 * _linearize(rgb.r) + 0.7152 * _linearize(rgb.g) + 0.0722 * _linearize(rgb.b)

    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def place(hexv: str) -> dict:
    l, a, b = lab(hexv)
    chroma = math.hypot(a, b)
    return {
        "hex": hexv,
        "h": math.degrees(math.atan2(b, a)) % 360,
        "l": l,
        "gray": chroma < GRAY_CHROMA,
        "light": l > LIGHT,
    }


def _in_gamut(linear: tuple[float, float, float]) -> bool:
    return all(-0.0005 <= v <= 1.0005 for v in linear)


def _max_chroma(l: float, hue: float) -> float:
    cos, sin = math.cos(math.radians(hue)), math.sin(math.radians(hue))
    lo, hi = 0.0, 0.4
    for _ in range(11):
        mid = (lo + hi) / 2
        if _in_gamut(oklab_to_linear(l, mid * cos, mid * sin)):
            lo = mid
        else:
            hi = mid
    return lo


def _rgb_from_lch(l: float, hue: float, fraction: float) -> RGB:
    chroma = _max_chroma(l, hue) * fraction
    return linear_to_rgb(oklab_to_linear(
        l, chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))))


def from_lch(l: float, hue: float, fraction: float) -> str:
    """The color at this lightness and hue, at a fraction of the most chroma sRGB can show there."""
    return rgb_to_hex(_rgb_from_lch(l, hue, fraction))


_grid: list[tuple[str, Lab]] | None = None


def _candidates() -> list[tuple[str, Lab]]:
    global _grid
    if _grid is None:
        steps = range(0, 256, GRID_STEP)
        _grid = []
        for r in steps:
            for g in steps:
                for b in steps:
                    rgb = RGB(r, g, b)
                    _grid.append((rgb_to_hex(rgb), rgb_to_oklab(rgb)))
    return _grid


def gaps(taken: list[str], band: str, count: int = 6) -> list[str]:
    """Colors farthest from every taken color and from the picks before them."""
    lo, hi = BANDS[band]
    pool = [(h, p) for h, p in _candidates()
            if lo <= p[0] <= hi and math.hypot(p[1], p[2]) >= MIN_GAP_CHROMA]
    taken_labs = [lab(h) for h in taken]
    nearest = [min((distance(p, t) for t in taken_labs), default=math.inf) for _, p in pool]
    picks = []
    for _ in range(count):
        i = max(range(len(pool)), key=nearest.__getitem__)
        hexv, point = pool[i]
        picks.append(hexv)
        nearest = [min(d, distance(p, point)) for d, (_, p) in zip(nearest, pool)]
    return picks


def near(hue: float, l: float, gray: bool) -> list[dict]:
    """The swatches offered for a click at this hue and lightness."""
    if gray:
        spec = [(0, 0, "gray"), (0.08, 0, "lighter"), (-0.08, 0, "darker"),
                (0.16, 0, "lighter still"), (-0.16, 0, "darker still")]
    else:
        spec = [(0, 0.97, "vivid"), (0, 0.6, "medium"), (0, 0.3, "muted"),
                (0.1, 0.97, "lighter"), (-0.1, 0.97, "darker")]
    return [
        dict(place(from_lch(min(0.97, max(0.08, l + shift)), hue, fraction)), tag=tag)
        for shift, fraction, tag in spec
    ]


def neighbors(hexv: str, repos: list[dict], count: int = 5) -> list[dict]:
    """The repos whose colors are closest to this one, nearest first."""
    point = lab(hexv)
    ranked = sorted(repos, key=lambda r: distance(point, lab(r["hex"])))
    out = []
    for repo in ranked[:count]:
        d = distance(point, lab(repo["hex"]))
        out.append({"name": repo["name"], "hex": repo["hex"], "sfkey": repo["sfkey"],
                    "distance": round(d, 3), "close": d < CLOSE})
    return out


def _png(width: int, height: int, rows: list[bytes]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def field_png(width: int = 180, height: int = 80) -> bytes:
    """The map's backdrop: hue left to right, lightness bottom to top."""
    rows = []
    for j in range(height):
        l = 1 - j / (height - 1)
        row = bytearray()
        for i in range(width):
            rgb = _rgb_from_lch(l, 360 * i / (width - 1), FIELD_CHROMA)
            row += bytes((rgb.r, rgb.g, rgb.b))
        rows.append(bytes(row))
    return _png(width, height, rows)


def grays_png(height: int = 80) -> bytes:
    rows = []
    for j in range(height):
        rgb = _rgb_from_lch(1 - j / (height - 1), 0, 0)
        rows.append(bytes((rgb.r, rgb.g, rgb.b)))
    return _png(1, height, rows)
