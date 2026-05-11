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
