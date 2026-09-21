# hued

Change terminal colors declaratively by directory.

Place a `.hued` file anywhere in your project tree:

```ini
# https://github.com/orochi235/hued
background=#1a0a0a
foreground=#c8ff59
```

When you `cd` into that directory (or any subdirectory), your terminal background changes. When you leave, it resets. The nearest `.hued` walking up from `$PWD` wins.

Named colors come from the CSS Color Module Level 4 list (148 names,
authoritative) plus the [xkcd color survey](https://xkcd.com/color/rgb.txt)
(839 more, CC0) — 987 in total. Multi-word xkcd names work with or without the
spaces: `hued set "baby poop green"` and `hued set babypoopgreen` are the same.

```zsh
hued set bg midnightblue
```

95 names appear in both lists. CSS wins by default, so `hued set red` is
`#ff0000`. Pass `-x` (or `--xkcd`) to prefer xkcd's reading instead:

```zsh
hued set red        # #ff0000  (CSS)
hued -x set red     # #e50000  (xkcd)
hued -x -i          # the picker, speaking xkcd
```

`hued get bg --name` reverses the lookup: it prints the name of the closest
color to whatever the channel holds. Without `-x` the search runs over the
CSS-wins list, so an xkcd-flavored hex lands on an xkcd-only name — `#e50000`
reports `fireenginered`, and only `hued -x get bg --name` calls it `red`.

hued always **stores a hex value** so any tool reading `.hued` gets a usable color without needing the name table. The original name is kept as an inline comment:

```ini
background=#191970  # midnightblue
```

Everything after the value on a line is treated as a comment and ignored when parsing.

## Keys

`.hued` holds one `key=value` per line. hued paints `background` and
`foreground`; the other keys are identity metadata it stores for other tools to
read — **nothing in hued renders `accent` or mints branch colors yet.**

```ini
background=#470013
foreground=#ffffff
accent=#ccff00              # a highlight color, for tools that draw one
branch-hue=+30deg..+90deg   # the range a per-branch color is minted from
branch-lightness=22%..38%
branch-chroma=70%..100%
sfkey=paintbrush.pointed.fill  # an SF Symbol name, for tools that draw an icon
```

`accent` is a color like the other two, names and all. The `branch-*` keys are
ranges: a signed endpoint is relative to this repo's own color, an unsigned one
is absolute, and a range has to be all one or the other — the same rule `mod`
uses. A lone value stands for a degenerate range. `sfkey` is stored as given,
even when it happens to be a color name too, like `leaf`.

`get`, `set` and `unset` take any of these keys:

```zsh
hued set accent limegreen        # accent=#32cd32  # limegreen
hued set branch-hue +30deg..+90deg
hued set sfkey leaf
hued get accent --name           # limegreen
hued unset branch-chroma
```

Bare `hued` prints `background` and `foreground`. `hued -a` prints every key the
file holds.

## Install

### Homebrew (recommended)

```zsh
brew tap orochi235/hued
brew install hued
```

Then add to your shell config:

**Zsh** (`~/.zshrc`):
```zsh
source "$(brew --prefix)/share/hued.sh"
precmd_functions+=(_hued_apply)
```

**Bash** (`~/.bashrc`):
```bash
source "$(brew --prefix)/share/hued.sh"
PROMPT_COMMAND="_hued_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
```

**Fish**:
```fish
cp (brew --prefix)/share/hued.fish ~/.config/fish/conf.d/hued.fish
```

### Manual

Clone the repo and source the script directly:

**Zsh**:
```zsh
source /path/to/hued.sh
precmd_functions+=(_hued_apply)
```

**Bash**:
```bash
source /path/to/hued.sh
PROMPT_COMMAND="_hued_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
```

**Fish**: copy `hued.fish` to `~/.config/fish/conf.d/hued.fish`.

## CLI

```
hued                              # print background and foreground
hued -a                           # print every key in the controlling .hued
hued [-x] <command>               # -x: prefer xkcd values for the 92 shared names
hued where                        # print path to the controlling .hued file
hued get <key> [--name]           # print a key's resolved hex, or its nearest name
hued set <color>                  # set background color
hued set <key> <value>            # set a named key
hued unset <key>                  # remove a key
hued mod [bg|fg] <op> [<args>]... # apply pastel transforms to a channel
hued apply                        # repaint the terminal to match the current .hued
hued resolve <color>              # print canonical #rrggbb for a color (requires pastel)
hued pack [<dir>] [-o <file>]     # export all .hued files under <dir> to JSON
hued unpack <file> [--force]      # restore .hued files from a JSON export
hued -i [--live]                  # open interactive color picker
```

`set` also accepts a color from stdin when no color argument is given, so pipelines work:

```
pastel darken 0.2 red | pastel format hex | hued set bg
```

`mod` (alias: `adjust`) is sugar for the read-transform-write loop. The channel
is optional and defaults to `bg`. Ops chain, and the whole chain produces one
write to `.hued`.

Amounts are percentages: `20%` and `20` mean the same thing, and a bare `0.2`
is rejected as ambiguous. A negative amount runs the opposite op, so
`darken -10%` is `lighten 10%`. For `lightness`, `saturation` and `hue`, a
leading `+` or `-` makes the value relative; unsigned sets the HSL component
absolutely.

```
hued mod darken 20%         # channel omitted, so this is the background
hued mod bg darken -10%     # same as: hued mod bg lighten 10%
hued mod fg rotate 30deg
hued mod bg mix '#0000ff' 25%
hued mod bg lightness 40%   # unsigned: HSL lightness becomes 40%
hued mod bg lightness +10%  # signed: relative, same as lighten 10%
hued mod bg hue +30deg
hued mod bg darken 10% rotate 30deg desaturate 5%   # chained, one write
```

Ops:

- `darken`, `lighten`, `saturate`, `desaturate` — `<amount>`, e.g. `20%`, `20`, `-10%`
- `rotate` — `<degrees>`, e.g. `30`, `30deg`, `30°`, `-90`
- `complement`, `to-gray` — no arguments
- `mix` — `<other-color> [<ratio>]`, ratio defaults to `50%`
- `lightness`, `saturation` — `<value>`, e.g. `40%`, `+10%`
- `hue` — `<degrees>`, e.g. `200deg`, `+30deg`

`pack` defaults to the current directory if none is given. `unpack` skips existing `.hued` files unless `--force` is passed. `get`, `mod`, and `resolve` all shell out to [`pastel`](https://github.com/sharkdp/pastel) (`brew install pastel`); `pastel` accepts named colors, hex, `rgb()`, `hsl()`, etc.

## Interactive picker

`hued -i` opens a fullscreen terminal color picker. Use the arrow keys to
adjust colors by channel, tab between panes, and press Enter to confirm.
The selected colors are written to the nearest `.hued` file.

Pass `--live` to apply colors immediately as you move sliders:

```zsh
hued -i --live
```

**Requirements:** Python 3.9 or later.

The picker is implemented in stdlib-only Python and ships as part of the hued
package. Homebrew installations include Python 3.12 as a dependency.

## Environment variables

`HUED_BACKGROUND` and `HUED_FOREGROUND` override the nearest `.hued` file on a per-channel basis. This lets [direnv](https://direnv.net/), mise, devenv, or any tool that manages per-directory environment also drive terminal colors:

```bash
# .envrc
export HUED_BACKGROUND=midnightblue
export HUED_FOREGROUND='#c8ff59'
```

When direnv unloads the variables (you `cd` out of the directory), the next prompt falls back to whatever `.hued` applies — or resets if none does.

Set a value to `none` to explicitly suppress that channel, even if a parent `.hued` would set it. This works in both env vars and `.hued` files:

```ini
# subdir/.hued — opt out of parent's background, keep its foreground
background=none
```

`hued set`, `unset`, `mod`, `fork`, and `unpack` repaint the current terminal
immediately (they emit the color escapes to your terminal after writing the
file), so you no longer have to wait for the next prompt. You can also force a
repaint anytime with `hued apply` — handy after editing a `.hued` by hand.

`HUED_LOOKUP_PREFER_XKCD` is the standing form of `-x`: export it and every
lookup — CLI and prompt hook alike — prefers xkcd's value for the 92 names the
two lists disagree on. It is off when unset, empty, `0`, `n`, `no`,
`off` or `false` (any case) and on for anything else; unlike hued's other
variables, `=0` really does mean off. `-x` cannot turn it back off, so clear it for one command to get
the CSS reading:

```bash
HUED_LOOKUP_PREFER_XKCD= hued set red   # #ff0000, just this once
```

Note: the prompt hook prefers the `hued` binary when it is on your `PATH`. For
`HUED_BACKGROUND` / `HUED_FOREGROUND` to take effect through it, **export** them
(tools like direnv and mise already do). A non-exported shell variable is only
honored by the hook's built-in fallback.

## FAQ

**Is hued a daemon?**
No. Calm down, Tucker.

## Terminal support

Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.
