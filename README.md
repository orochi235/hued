# hued

Set your terminal colors per directory, like `.editorconfig` for your terminal.

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
hued                   # print current colors
hued set <color>       # set background color (shorthand)
hued set bg <color>    # set background color
hued set fg <color>    # set foreground color
hued where             # print the path to the controlling .hued file
```

## Terminal support

Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.
