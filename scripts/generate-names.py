#!/usr/bin/env python3
"""Generate hued-names.sh and src/huedmap/names.py from CSS + xkcd color names.

Sources:
  - CSS Color Module Level 4 named colors (148), hardcoded below. Stable since
    rebeccapurple was added in 2014.
  - The xkcd color survey (934), CC0: https://xkcd.com/color/rgb.txt

CSS wins the 95 names both define. The 92 of those where the two disagree are
emitted a second time under "xkcd:<name>" keys so `hued -x` can prefer them
without needing a second file.

Run: make color-names
"""
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XKCD_URL = "https://xkcd.com/color/rgb.txt"

CSS_NAMES = {
    "aliceblue": "#f0f8ff", "antiquewhite": "#faebd7", "aqua": "#00ffff",
    "aquamarine": "#7fffd4", "azure": "#f0ffff", "beige": "#f5f5dc",
    "bisque": "#ffe4c4", "black": "#000000", "blanchedalmond": "#ffebcd",
    "blue": "#0000ff", "blueviolet": "#8a2be2", "brown": "#a52a2a",
    "burlywood": "#deb887", "cadetblue": "#5f9ea0", "chartreuse": "#7fff00",
    "chocolate": "#d2691e", "coral": "#ff7f50", "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc", "crimson": "#dc143c", "cyan": "#00ffff",
    "darkblue": "#00008b", "darkcyan": "#008b8b", "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9", "darkgreen": "#006400", "darkgrey": "#a9a9a9",
    "darkkhaki": "#bdb76b", "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f", "darkorange": "#ff8c00",
    "darkorchid": "#9932cc", "darkred": "#8b0000", "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f", "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f", "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1", "darkviolet": "#9400d3", "deeppink": "#ff1493",
    "deepskyblue": "#00bfff", "dimgray": "#696969", "dimgrey": "#696969",
    "dodgerblue": "#1e90ff", "firebrick": "#b22222", "floralwhite": "#fffaf0",
    "forestgreen": "#228b22", "fuchsia": "#ff00ff", "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff", "gold": "#ffd700", "goldenrod": "#daa520",
    "gray": "#808080", "green": "#008000", "greenyellow": "#adff2f",
    "grey": "#808080", "honeydew": "#f0fff0", "hotpink": "#ff69b4",
    "indianred": "#cd5c5c", "indigo": "#4b0082", "ivory": "#fffff0",
    "khaki": "#f0e68c", "lavender": "#e6e6fa", "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00", "lemonchiffon": "#fffacd", "lightblue": "#add8e6",
    "lightcoral": "#f08080", "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2", "lightgray": "#d3d3d3",
    "lightgreen": "#90ee90", "lightgrey": "#d3d3d3", "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a", "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa", "lightslategray": "#778899",
    "lightslategrey": "#778899", "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0", "lime": "#00ff00", "limegreen": "#32cd32",
    "linen": "#faf0e6", "magenta": "#ff00ff", "maroon": "#800000",
    "mediumaquamarine": "#66cdaa", "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3", "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371", "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a", "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585", "midnightblue": "#191970",
    "mintcream": "#f5fffa", "mistyrose": "#ffe4e1", "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead", "navy": "#000080", "oldlace": "#fdf5e6",
    "olive": "#808000", "olivedrab": "#6b8e23", "orange": "#ffa500",
    "orangered": "#ff4500", "orchid": "#da70d6", "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98", "paleturquoise": "#afeeee",
    "palevioletred": "#db7093", "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9", "peru": "#cd853f", "pink": "#ffc0cb",
    "plum": "#dda0dd", "powderblue": "#b0e0e6", "purple": "#800080",
    "rebeccapurple": "#663399", "red": "#ff0000", "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1", "saddlebrown": "#8b4513", "salmon": "#fa8072",
    "sandybrown": "#f4a460", "seagreen": "#2e8b57", "seashell": "#fff5ee",
    "sienna": "#a0522d", "silver": "#c0c0c0", "skyblue": "#87ceeb",
    "slateblue": "#6a5acd", "slategray": "#708090", "slategrey": "#708090",
    "snow": "#fffafa", "springgreen": "#00ff7f", "steelblue": "#4682b4",
    "tan": "#d2b48c", "teal": "#008080", "thistle": "#d8bfd8",
    "tomato": "#ff6347", "turquoise": "#40e0d0", "violet": "#ee82ee",
    "wheat": "#f5deb3", "white": "#ffffff", "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00", "yellowgreen": "#9acd32",
}


def normalize(name: str) -> str:
    """Lowercase and strip spaces, hyphens and apostrophes."""
    return re.sub(r"[ \-'’]", "", name.lower())


def fetch_xkcd() -> tuple[dict[str, str], int]:
    """Return (key -> hex, collision count).

    Upstream spells some colors both ways ("light blue" and "lightblue"),
    which normalize to one key. The spelling that already equals the key
    wins; upstream order decides nothing.
    """
    with urllib.request.urlopen(XKCD_URL) as resp:
        text = resp.read().decode("utf-8")
    out: dict[str, str] = {}
    winner: dict[str, str] = {}
    collisions = 0
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2 or not parts[1].startswith("#"):
            continue
        raw, key = parts[0], normalize(parts[0])
        if key in out:
            collisions += 1
            if winner[key] == key or raw != key:
                continue
        out[key] = parts[1].strip().lower()
        winner[key] = raw
    return out, collisions


def main() -> int:
    xkcd, collisions = fetch_xkcd()
    if len(xkcd) < 900:
        sys.exit(f"xkcd list looks truncated: {len(xkcd)} entries")

    merged = dict(xkcd)
    merged.update(CSS_NAMES)                      # CSS wins the overlaps
    overrides = {k: v for k, v in xkcd.items()
                 if k in CSS_NAMES and v != CSS_NAMES[k]}

    # Both shell hooks and bin/hued grep hued-names.sh for "[<key>]=" and
    # reject keys outside this alphabet, so an upstream name carrying a regex
    # metacharacter, a bracket, or an "xkcd:" prefix must fail here loudly
    # rather than become an unreachable row.
    for key in merged:
        if not re.fullmatch(r"[a-z0-9/]+", key):
            sys.exit(f"key {key!r} is outside the grep-safe [a-z0-9/] alphabet")

    header = (
        "# Generated by scripts/generate-names.py — do not edit by hand\n"
        "# Sources: CSS Color Module Level 4 (148 names, authoritative)\n"
        "#          https://xkcd.com/color/rgb.txt (CC0)\n"
        "# 'xkcd:<name>' keys are xkcd's value for a name CSS also defines,\n"
        "# selected by `hued -x`.\n"
    )

    sh = [header, "declare -A _HUED_NAMES=("]
    for k in sorted(merged):
        sh.append(f"  [{k}]={merged[k]}")
    for k in sorted(overrides):
        sh.append(f"  [xkcd:{k}]={overrides[k]}")
    sh.append(")")
    (ROOT / "hued-names.sh").write_text("\n".join(sh) + "\n")

    py = [
        "# Generated by scripts/generate-names.py — do not edit by hand.",
        "# Sources: CSS Color Module Level 4 (authoritative) + xkcd (CC0).",
        "",
        "NAMED_COLORS: dict[str, str] = {",
    ]
    for k in sorted(merged):
        py.append(f'    "{k}": "{merged[k]}",')
    py.append("}")
    py.append("")
    py.append("# xkcd's value for names CSS also defines; merged over")
    py.append("# NAMED_COLORS when the user passes -x.")
    py.append("XKCD_OVERRIDES: dict[str, str] = {")
    for k in sorted(overrides):
        py.append(f'    "{k}": "{overrides[k]}",')
    py.append("}")
    py.append("")
    (ROOT / "src" / "huedmap" / "names.py").write_text("\n".join(py))

    print(f"{len(merged)} names ({len(CSS_NAMES)} CSS + "
          f"{len(merged) - len(CSS_NAMES)} xkcd-only), "
          f"{len(overrides)} xkcd overrides, "
          f"{collisions} xkcd spelling collisions resolved")
    print(f"wrote {ROOT / 'hued-names.sh'}")
    print(f"wrote {ROOT / 'src' / 'huedmap' / 'names.py'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
