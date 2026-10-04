"""Reading and writing .hued files in bulk: what `hued pack`, `unpack` and `map` share."""
from __future__ import annotations

import json
import os
import re
import sys

from .names import NAMED_COLORS, XKCD_OVERRIDES

HEADER = "# https://github.com/orochi235/hued\n"
COLOR_KEYS = {"background", "foreground", "accent", "accent2", "accent3"}

# Never hold a .hued worth finding, and walking them is most of a scan's time.
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}


def read(path) -> dict[str, str]:
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            # The value is the first token; the rest is an inline comment.
            tokens = value.split()
            if tokens:
                config[key.strip()] = tokens[0]
    return config


def scan(root) -> dict[str, dict[str, str]]:
    found = {}
    for dirpath, dirs, names in os.walk(str(root)):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        if ".hued" in names:
            config = read(os.path.join(dirpath, ".hued"))
            if config:
                found[dirpath] = config
    return found


def name_key(name: str) -> str:
    return re.sub(r"[ \-'’]", "", name.lower())


def normalize(value: str, xkcd: bool = False) -> tuple[str, str | None]:
    """Return (hex or the value unchanged, the color name it was written as or None)."""
    tokens = value.split()
    v = tokens[0] if tokens else value
    bare = v[1:] if v.startswith("#") else v
    if re.fullmatch(r"[0-9a-fA-F]{3}", bare):
        bare = "".join(c * 2 for c in bare)
    if re.fullmatch(r"[0-9a-fA-F]{6}", bare):
        return "#" + bare.lower(), None
    if v.lower() == "none":
        return "none", None
    key = name_key(value)
    hexv = (XKCD_OVERRIDES.get(key) if xkcd else None) or NAMED_COLORS.get(key)
    if hexv:
        return hexv, value.strip()
    return v, None


def unpack(path, force: bool, xkcd: bool = False) -> None:
    with open(path) as f:
        data = json.load(f)
    for dirpath, config in data.items():
        hued_path = os.path.join(dirpath, ".hued")
        if os.path.exists(hued_path) and not force:
            print(f"Skipping {hued_path} (already exists, use --force to overwrite)", file=sys.stderr)
            continue
        os.makedirs(dirpath, exist_ok=True)
        with open(hued_path, "w") as f:
            f.write(HEADER)
            for key, value in config.items():
                if key not in COLOR_KEYS:
                    f.write(f"{key}={value}\n")
                    continue
                hexv, name = normalize(value, xkcd)
                f.write(f"{key}={hexv}  # {name}\n" if name else f"{key}={hexv}\n")
        print(f"Wrote {hued_path}")


def main(argv: list[str]) -> int:
    xkcd = "--xkcd" in argv
    args = [a for a in argv if a != "--xkcd"]
    if len(args) == 2 and args[0] == "pack":
        print(json.dumps(scan(args[1]), indent=2))
        return 0
    if len(args) == 3 and args[0] == "unpack":
        unpack(args[1], force=args[2] == "1", xkcd=xkcd)
        return 0
    print("usage: python3 -m huedmap.files pack <dir> | unpack <file> <0|1> [--xkcd]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
