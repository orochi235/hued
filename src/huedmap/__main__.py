"""hued map — open a page of the colors in use and write the one picked.

Run:
  python3 -m huedmap --hued <path to hued> [<dir>] [--no-open] [--xkcd]
"""
from __future__ import annotations

import argparse
import os
import secrets
import signal
import sys
import threading
import webbrowser

from . import server, symbols


def _cancel(*_):
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hued map", description=(
        "Open a page showing every background in use under <dir>, suggest unused ones, "
        "and write the one you pick to .hued in the current directory."))
    parser.add_argument("dir", nargs="?", help="directory to scan (default: the parent of this one)")
    parser.add_argument("--no-open", action="store_true", help="print the URL instead of opening a browser")
    parser.add_argument("--hued", required=True, help=argparse.SUPPRESS)
    parser.add_argument("--xkcd", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    target = os.getcwd()
    root = os.path.abspath(args.dir) if args.dir else os.path.dirname(target)
    if not os.path.isdir(root):
        print(f"hued map: {root} is not a directory", file=sys.stderr)
        return 1

    print(f"Scanning {root} ...", flush=True)
    repos = server.load_repos(root, target, args.xkcd)
    print(f"Found {len(repos)} backgrounds in use.", flush=True)

    glyphs = symbols.Glyphs() if symbols.Glyphs.available() else None
    app = server.App(repos, root, target, os.path.abspath(args.hued), secrets.token_urlsafe(16),
                     index=symbols.Index.load() if glyphs else None, glyphs=glyphs)
    httpd = server.make_server(app)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    address = server.url(httpd, app.token)
    print(address, flush=True)
    print("Waiting for a pick. Ctrl-C to cancel.", flush=True)
    if not args.no_open:
        webbrowser.open(address)

    signal.signal(signal.SIGTERM, _cancel)
    try:
        reason = server.wait(app)
    except KeyboardInterrupt:
        reason = "canceled"
    finally:
        httpd.shutdown()
        httpd.server_close()
        if glyphs:
            glyphs.close()

    if reason == "picked":
        print(f"Wrote {os.path.join(target, '.hued')}:")
        for line in app.written:
            print(f"  {line}")
    else:
        why = {"closed": "Page closed. ", "canceled": "",
               "idle": f"No activity for {server.IDLE_SECONDS // 60} minutes. "}[reason]
        print(f"{why}Nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
