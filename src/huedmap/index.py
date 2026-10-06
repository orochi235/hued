"""The directories known to hold a .hued, so `hued map` need not walk a tree to find them.

One absolute path per line. `hued set` and `unpack` add to it, `pack` replaces the part under
the tree it walked, and every read drops directories whose .hued is gone.
"""
from __future__ import annotations

import os
import sys

from . import files


def path() -> str:
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(cache, "hued", "index")


def _under(dirpath: str, root: str) -> bool:
    return dirpath == root or dirpath.startswith(root.rstrip(os.sep) + os.sep)


def load() -> list[str] | None:
    """The indexed directories, or None when there is no index yet."""
    try:
        with open(path()) as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    except FileNotFoundError:
        return None


def save(dirs) -> None:
    out = path()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        f.writelines(d + "\n" for d in sorted(set(dirs)))
    os.replace(tmp, out)


def add(dirpath: str) -> None:
    dirpath = os.path.realpath(dirpath)
    dirs = load() or []
    if dirpath not in dirs:
        save(dirs + [dirpath])


def refresh(root: str, found) -> None:
    """Make the index under root exactly what a walk of root found."""
    root = os.path.realpath(root)
    kept = [d for d in load() or [] if not _under(d, root)]
    save(kept + [os.path.realpath(d) for d in found])


def configs(root: str) -> dict[str, dict[str, str]]:
    """Every .hued under root, read through the index; walks root and seeds it when there is none."""
    root = os.path.realpath(root)
    dirs = load()
    if dirs is None:
        found = files.scan(root)
        refresh(root, found)
        return {os.path.realpath(d): c for d, c in found.items()}
    found, gone = {}, []
    for d in dirs:
        hued = os.path.join(d, ".hued")
        if not os.path.isfile(hued):
            gone.append(d)
        elif _under(d, root):
            config = files.read(hued)
            if config:
                found[d] = config
    if gone:
        save(d for d in dirs if d not in gone)
    return found


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "add":
        add(argv[1])
        return 0
    print("usage: python3 -m huedmap.index add <dir>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
