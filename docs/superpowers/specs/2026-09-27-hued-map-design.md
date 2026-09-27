# `hued map` — design

**What this is:** a design for a command that opens a web page showing every color already
in use under a directory, suggests unused ones, and writes the one you pick to `.hued`.
**Who it's for:** whoever builds it. Assumes you know hued but not the session that designed it.
**Status:** designed 2026-09-27. **Nothing here is built.**

## What the user does

```zsh
cd ~/src/newrepo
hued map            # scans ~/src, opens the page, waits
```

The page opens in the default browser. They pick a color, optionally a symbol, and press
"Use this". The command writes `.hued` in the directory it was run from, repaints the terminal,
and exits.

```
hued map [<dir>] [--no-open]
```

`<dir>` is the directory scanned for `.hued` files; the default is the parent of the current
directory. `--no-open` prints the URL instead of opening a browser.

## The page

**Map.** A rectangle with hue left to right and lightness bottom to top, both measured in OKLCH
(a color space where equal distances look equally different). Each scanned `background` is a dot
in its own color. Colors with almost no saturation have no meaningful hue, so they go in a
separate "grays" column on the left. Hovering a dot shows the repo's path, hex and symbol.

Saturation is not on the map. Two colors at the same hue and lightness land on the same spot
however vivid they are; the "close to" flag below is what catches that.

**Widest gaps.** Six suggested colors, each the one farthest from every color in use and from
the suggestions before it. A control limits them to "any lightness", "dark only" or "light
only". Grays and near-black are never suggested, since near-black is most terminals' default.
They appear on the map as numbered dashed rings.

**From your click.** Clicking the map gives five swatches at that hue and lightness: vivid,
medium, muted, lighter, darker. Clicking the grays column gives five grays around that lightness.

**Swatch.** Shows the color, its hex, and the nearest repo in use. When that repo is near enough
to be confused with it, the line reads "close to `<repo>`" in the warning color.

**Preview.** The selected swatch drawn as a terminal, with the exact lines "Use this" will write,
beside a list of the five closest repos in use and their distances.

**Symbol.** A field for the new repo's `sfkey`, an SF Symbol name. A symbol another repo already
uses is marked "taken: `<repo>`" but can still be chosen.

## What gets written

| Key | When |
|---|---|
| `background` | always |
| `sfkey` | when a symbol was chosen |
| `foreground=#000000` | when the background's OKLCH lightness is above 0.6 |

Writes go through `hued set`, run in the launch directory, so name handling, file format and
the repaint stay in the one place that already does them. An existing `.hued` keeps its other
keys.

## How it is built

A Python package, `src/huedmap/`, standard library only, launched the way the picker is.

| Module | Job |
|---|---|
| `scan` | Walk a directory and return each `.hued` file's keys. `hued pack` calls this too; its inline copy in `bin/hued` is deleted. |
| `color` | Distance between colors, the widest-gap search, the click swatches, the map's background raster. Builds on the OKLCH conversions already in `picker/colors.py`. |
| `symbols` | macOS only: glyph images and symbol search. |
| `server` | Serves the page and the endpoints below. |
| `page.html` | The page. Draws what the server sends; does no color math of its own. |

All color math lives in Python so that it runs under pytest. The repo has no JavaScript test
runner, and suggestions that ship untested are the part most likely to be quietly wrong.

`hued-pick` resolves where the Python packages live (Homebrew's `libexec` or the source tree).
That resolution moves somewhere both launchers and `pack` share.

### Server

Binds `127.0.0.1` on a random port. The URL carries a one-time token and every request must
present it, because the server can write a file.

| Request | Returns |
|---|---|
| `GET /` | the page |
| `GET /data` | scanned repos, the map raster, the widest gaps for each lightness limit, which symbol features this platform has |
| `GET /near?h=&l=` | the five click swatches, each with its closest repos |
| `GET /symbols?q=` | matching symbol names, with glyphs |
| `POST /use` | writes `.hued`, then the server exits |
| `POST /bye` | sent when the tab closes; the server exits without writing |

It also exits on Ctrl-C and after 15 minutes without a request.

### Symbols

A browser cannot draw an SF Symbol from its name. On macOS the server starts one Swift helper
process that takes symbol names and returns PNGs drawn by AppKit; it ends with the server.
Measured on 2026-09-27: a one-shot Swift script drew 36 glyphs in 1.4s, nearly all of it
startup, which is why the helper stays running rather than being launched per search.

Search reads the keyword index macOS ships in
`/System/Library/CoreServices/CoreGlyphs.bundle/Contents/Resources/`. `symbol_order.plist` lists
the names and `symbol_search.plist` maps some of them to keywords. Fewer than half the names
have keywords (`brain` has none), so search matches the name as well.

Without macOS, or without `swift` on the path, dots show no glyph, symbols are listed by name,
and the symbol field is plain text. Nothing else changes.

### Disk

Only `.hued` is written. The page, raster and glyphs are built in memory and served from there.

## Decisions that are guesses

- **"Close to" means an OKLab distance under 0.10.** Chosen by eye on one palette of 46 colors.
- **Lightness limits:** any is 0.20–0.92, dark is 0.20–0.50, light is 0.60–0.92.

## Tests

| Where | What |
|---|---|
| pytest | Widest gaps avoid colors in use and respect the lightness limit. Click swatches are in gamut and at the clicked hue. `scan` handles inline comments, `none`, named colors and nested files. The server rejects a missing token, and `POST /use` writes the expected lines to a temporary directory. |
| bats | `hued pack` output is unchanged. `hued map --no-open` prints a URL and exits on interrupt. |

The Swift helper's test is skipped off macOS.

## Also part of this change

- README and the three shell completions gain `map`.
- The Homebrew formula, in the separate `homebrew-hued` repo, installs `src/huedmap` and the
  launcher at the next release.

## Not included

A static page with no server, which was considered and declined. The `accent` and `branch-*`
keys. A saturation axis.
