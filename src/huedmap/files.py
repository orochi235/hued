"""Reading and writing .hued files in bulk: what `hued pack`, `unpack` and `map` share."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

from . import index
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


def scan(root, on_found=None) -> dict[str, dict[str, str]]:
    """Every .hued under root; on_found(dir, config) hears of each one as the walk reaches it."""
    found = {}
    for dirpath, dirs, names in os.walk(str(root)):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        if ".hued" in names:
            config = read(os.path.join(dirpath, ".hued"))
            if config:
                found[dirpath] = config
                if on_found:
                    on_found(dirpath, config)
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


KEY = re.compile(r"[A-Za-z0-9_]+")


def problems(data) -> list[str]:
    """Why a pack manifest can't be unpacked; empty when it can."""
    if not isinstance(data, dict):
        return ["the manifest is not a JSON object of directory -> settings"]
    out = []
    for dirpath, config in data.items():
        if not dirpath:
            out.append("an entry has an empty directory")
            continue
        if not isinstance(config, dict):
            out.append(f"{dirpath}: settings are not an object")
            continue
        for key, value in config.items():
            if not KEY.fullmatch(key):
                out.append(f"{dirpath}: {key!r} is not a valid key")
            elif not isinstance(value, str) or "\n" in value or "\r" in value:
                out.append(f"{dirpath}: {key} must be a single-line string")
    return out


def render(config: dict[str, str], xkcd: bool) -> str:
    lines = [HEADER]
    for key, value in config.items():
        if key not in COLOR_KEYS:
            lines.append(f"{key}={value}\n")
            continue
        hexv, name = normalize(value, xkcd)
        lines.append(f"{key}={hexv}  # {name}\n" if name else f"{key}={hexv}\n")
    return "".join(lines)


def _replace(path: str, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".hued.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def unpack(path, force: bool, xkcd: bool = False) -> None:
    """Writes every entry of a pack manifest, after checking the whole manifest first."""
    with open(path) as f:
        data = json.load(f)
    bad = problems(data)
    if bad:
        raise ValueError("nothing unpacked:\n  " + "\n  ".join(bad))
    for dirpath, config in data.items():
        hued_path = os.path.join(dirpath, ".hued")
        text = render(config, xkcd)
        os.makedirs(dirpath, exist_ok=True)
        if force:
            _replace(hued_path, text)
        else:
            try:
                with open(hued_path, "x") as f:
                    f.write(text)
            except FileExistsError:
                print(f"Skipping {hued_path} (already exists, use --force to overwrite)", file=sys.stderr)
                continue
        index.add(dirpath)
        print(f"Wrote {hued_path}")


def main(argv: list[str]) -> int:
    xkcd = "--xkcd" in argv
    args = [a for a in argv if a != "--xkcd"]
    if len(args) == 2 and args[0] == "pack":
        found = scan(args[1])
        index.refresh(args[1], found)
        print(json.dumps(found, indent=2))
        return 0
    if len(args) == 3 and args[0] == "unpack":
        try:
            unpack(args[1], force=args[2] == "1", xkcd=xkcd)
        except ValueError as e:
            print(f"hued unpack: {e}", file=sys.stderr)
            return 1
        return 0
    print("usage: python3 -m huedmap.files pack <dir> | unpack <file> <0|1> [--xkcd]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
