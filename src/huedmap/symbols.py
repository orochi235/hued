"""SF Symbols: searching the names macOS ships, and drawing them. macOS only."""
from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import threading

RESOURCES = "/System/Library/CoreServices/CoreGlyphs.bundle/Contents/Resources"
NAME = re.compile(r"[A-Za-z0-9.]+")


def valid(name: str) -> bool:
    return bool(NAME.fullmatch(name))


class Index:
    def __init__(self, names: list[str], keywords: dict[str, list[str]]):
        self.names = names
        self.keywords = keywords

    @classmethod
    def load(cls, directory: str = RESOURCES) -> "Index | None":
        try:
            with open(os.path.join(directory, "symbol_order.plist"), "rb") as f:
                names = plistlib.load(f)
            with open(os.path.join(directory, "symbol_search.plist"), "rb") as f:
                keywords = plistlib.load(f)
        except (OSError, plistlib.InvalidFileException):
            return None
        return cls(list(names), dict(keywords))

    def search(self, query: str, limit: int = 12) -> list[str]:
        """Names matching every word of the query, in the name itself or in its keywords."""
        words = query.lower().split()
        if not words:
            return []
        ranked = []
        for order, name in enumerate(self.names):
            keywords = self.keywords.get(name, [])
            if not all(w in name or any(w in k for k in keywords) for w in words):
                continue
            parts = name.split(".")
            first = words[0]
            rank = (0 if name == first
                    else 1 if first in parts
                    else 2 if name.startswith(first)
                    else 3 if any(p.startswith(first) for p in parts)
                    else 4 if first in name
                    else 5)
            ranked.append((rank, len(parts), order, name))
        return [name for *_, name in sorted(ranked)[:limit]]


class Glyphs:
    """One Swift helper process, kept for the life of the server, that draws symbols on request."""

    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()
        self._cache: dict[str, str | None] = {}

    @staticmethod
    def available() -> bool:
        return sys.platform == "darwin" and shutil.which("swift") is not None

    def _start(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyphs.swift")
        self._proc = subprocess.Popen(
            ["swift", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True)

    def get(self, names: list[str]) -> dict[str, str]:
        """Base64 PNGs for the names that could be drawn; the rest are left out."""
        names = [n for n in names if valid(n)]
        with self._lock:
            missing = [n for n in dict.fromkeys(names) if n not in self._cache]
            if missing:
                drawn = self._draw(missing)
                for name in missing:
                    self._cache[name] = drawn.get(name)
            return {n: self._cache[n] for n in names if self._cache.get(n)}

    def _draw(self, names: list[str]) -> dict[str, str]:
        try:
            if self._proc is None:
                self._start()
            self._proc.stdin.write(" ".join(names) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            return json.loads(line) if line else {}
        except (OSError, ValueError):
            return {}

    def close(self):
        with self._lock:
            if self._proc is None:
                return
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                self._proc.kill()
                self._proc.wait()
            self._proc = None
