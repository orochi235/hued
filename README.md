# hued

Change terminal colors declaratively by directory.

Place a `.hued` file anywhere in your project tree:

```ini
# https://github.com/orochi235/hued
background=#1a0a0a
foreground=#c8ff59
```

When you `cd` into that directory (or any subdirectory), your terminal background changes. When you leave, it resets. The nearest `.hued` walking up from `$PWD` wins.

Named colors from the [X11 rgb.txt](https://gitlab.freedesktop.org/xorg/app/rgb/-/raw/master/rgb.txt) list are supported in addition to hex values:

```ini
background=midnightblue
```

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
hued                          # print current colors
hued where                    # print path to the controlling .hued file
hued get bg|fg                # print the resolved hex for a channel
hued set <color>              # set background color
hued set bg|fg <color>        # set the named channel
hued mod bg|fg <op> [<args>]  # apply a pastel transform to a channel
hued resolve <color>          # print canonical #rrggbb for a color (requires pastel)
hued pack [<dir>] [-o <file>] # export all .hued files under <dir> to JSON
hued unpack <file> [--force]  # restore .hued files from a JSON export
hued -i [--live]              # open interactive color picker
```

`set` also accepts a color from stdin when no color argument is given, so pipelines work:

```
pastel darken 0.2 red | pastel format hex | hued set bg
```

`mod` (alias: `adjust`) is sugar for the read-transform-write loop. Supported ops:
`darken`, `lighten`, `saturate`, `desaturate` (amount as `0.2` or `20%`); `rotate` (`30` or `30deg`); `complement`, `to-gray` (no args); `mix <other-color> [<ratio>]` (ratio defaults to `0.5`).

```
hued mod bg darken 20%
hued mod fg rotate 30deg
hued mod bg mix '#0000ff' 0.25
```

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

## FAQ

**Is hued a daemon?**
No. Calm down, Tucker.

## Terminal support

Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.
