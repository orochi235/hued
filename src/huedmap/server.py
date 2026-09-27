"""The local server behind `hued map`: serves the page, answers its questions, writes the pick."""
from __future__ import annotations

import json
import math
import os
import re
import socketserver
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import color, files, symbols

IDLE_SECONDS = 15 * 60
# A reload closes the page and reopens it; wait this long for the reopen before treating it as goodbye.
LEAVE_SECONDS = 2
MAX_BODY = 64 * 1024
HEX = re.compile(r"#[0-9a-f]{6}")
DARK_TEXT = "#000000"


def writes(background: str, sfkey: str = "") -> list[tuple[str, str]]:
    """The keys a pick sets, in the order they are written."""
    out = [("bg", "background", background)]
    if color.place(background)["light"]:
        out.append(("fg", "foreground", DARK_TEXT))
    if sfkey:
        out.append(("sfkey", "sfkey", sfkey))
    return out


def load_repos(root: str, target: str, xkcd: bool = False) -> list[dict]:
    """Every background in use under root, except the one in the directory being colored."""
    repos = []
    for path, config in files.scan(root).items():
        if os.path.realpath(path) == os.path.realpath(target):
            continue
        hexv, _ = files.normalize(config.get("background", ""), xkcd)
        if not HEX.fullmatch(hexv):
            continue
        repos.append(dict(color.place(hexv),
                          name=os.path.relpath(path, root), sfkey=config.get("sfkey", "")))
    return sorted(repos, key=lambda r: r["name"])


class App:
    def __init__(self, repos, root, target, hued, token, index=None, glyphs=None, env=None):
        self.repos = repos
        self.root = root
        self.target = target
        self.hued = hued
        self.token = token
        self.index = index
        self.glyphs = glyphs
        self.env = env
        self.done = threading.Event()
        self.written: list[str] = []
        self.last_request = time.monotonic()
        self.leaving: float | None = None
        self._static: dict[str, bytes] = {}

    # --- what the page asks for ---

    def swatch(self, hexv: str, tag: str) -> dict:
        return dict(color.place(hexv), tag=tag,
                    neighbors=color.neighbors(hexv, self.repos),
                    writes=[f"{key}={value}" for _, key, value in writes(hexv)])

    def data(self) -> dict:
        taken = [r["hex"] for r in self.repos]
        current = {}
        own = os.path.join(self.target, ".hued")
        if os.path.exists(own):
            current = files.read(own)
        return {
            "root": self.root,
            "target": self.target,
            "name": os.path.basename(self.target),
            "current": current,
            "repos": self.repos,
            "gaps": {band: [self.swatch(h, f"gap {i + 1}")
                            for i, h in enumerate(color.gaps(taken, band))]
                     for band in color.BANDS},
            "symbols": {"search": self.index is not None, "glyphs": self.glyphs is not None},
        }

    def near(self, query: dict) -> dict:
        hue, lightness = float(query.get("h", "0")), float(query.get("l", "0.5"))
        if not (math.isfinite(hue) and math.isfinite(lightness)):
            raise ValueError("h and l must be numbers")
        hue, lightness = hue % 360, min(1.0, max(0.0, lightness))
        gray = query.get("gray") == "1"
        return {"swatches": [self.swatch(s["hex"], s["tag"])
                             for s in color.near(hue, lightness, gray)]}

    def find_symbols(self, query: dict) -> dict:
        taken = {}
        for repo in self.repos:
            if repo["sfkey"]:
                taken.setdefault(repo["sfkey"], repo["name"])
        names = self.index.search(query.get("q", "")) if self.index else []
        return {"names": [{"name": n, "taken": taken.get(n)} for n in names]}

    def draw(self, query: dict) -> dict:
        names = [n for n in query.get("names", "").split(",") if n]
        return self.glyphs.get(names) if self.glyphs else {}

    def use(self, body: bytes) -> dict:
        pick = json.loads(body or b"{}")
        background = str(pick.get("background", "")).lower()
        sfkey = str(pick.get("sfkey", "")).strip()
        if not HEX.fullmatch(background):
            raise ValueError("background must be #rrggbb")
        if sfkey and not symbols.valid(sfkey):
            raise ValueError("sfkey must be a symbol name")
        env = dict(os.environ, **(self.env or {}))
        lines = []
        for short, key, value in writes(background, sfkey):
            subprocess.run([self.hued, "set", short, value], cwd=self.target, env=env,
                           check=True, capture_output=True, text=True)
            lines.append(f"{key}={value}")
        self.written = lines
        self.done.set()
        return {"written": lines, "path": os.path.join(self.target, ".hued")}

    def static(self, name: str) -> bytes:
        if name not in self._static:
            if name == "page.html":
                here = os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(here, "page.html"), "rb") as f:
                    self._static[name] = f.read()
            elif name == "field.png":
                self._static[name] = color.field_png()
            else:
                self._static[name] = color.grays_png()
        return self._static[name]

    # --- routing ---

    def handle(self, method: str, target: str, body: bytes = b"") -> tuple[int, str, bytes]:
        url = urlsplit(target)
        query = {k: v[-1] for k, v in parse_qs(url.query).items()}
        if query.get("t") != self.token:
            return 403, "text/plain", b"forbidden\n"
        self.last_request = time.monotonic()
        self.leaving = None
        route = (method, url.path)
        try:
            if route == ("GET", "/"):
                return 200, "text/html; charset=utf-8", self.static("page.html")
            if route in (("GET", "/field.png"), ("GET", "/grays.png")):
                return 200, "image/png", self.static(url.path[1:])
            if route == ("GET", "/data"):
                return self._json(self.data())
            if route == ("GET", "/near"):
                return self._json(self.near(query))
            if route == ("GET", "/symbols"):
                return self._json(self.find_symbols(query))
            if route == ("GET", "/glyphs"):
                return self._json(self.draw(query))
            if route == ("POST", "/use"):
                return self._json(self.use(body))
            if route == ("POST", "/bye"):
                self.leaving = time.monotonic()
                return self._json({})
        except ValueError as e:
            return 400, "text/plain", f"{e}\n".encode()
        except subprocess.CalledProcessError as e:
            return 500, "text/plain", (e.stderr or str(e)).encode()
        return 404, "text/plain", b"not found\n"

    @staticmethod
    def _json(value) -> tuple[int, str, bytes]:
        return 200, "application/json", json.dumps(value).encode()

    def finished(self) -> str | None:
        """Why the server should stop now, or None to keep going."""
        now = time.monotonic()
        if self.done.is_set():
            return "picked"
        if self.leaving is not None and now - self.leaving > LEAVE_SECONDS:
            return "closed"
        if now - self.last_request > IDLE_SECONDS:
            return "idle"
        return None


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):
        # HTTPServer's own bind looks up the host's name, a reverse DNS query that can take 30s.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def make_server(app: App) -> Server:
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, body: bytes = b""):
            status, kind, payload = app.handle(self.command, self.path, body)
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            self._respond()

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self.send_error(413)
                return
            self._respond(self.rfile.read(length))

        def log_message(self, *args):
            pass

    return Server(("127.0.0.1", 0), Handler)


def url(server: Server, token: str) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}/?t={token}"


def wait(app: App, poll: float = 0.25) -> str:
    while True:
        reason = app.finished()
        if reason:
            return reason
        app.done.wait(poll)
