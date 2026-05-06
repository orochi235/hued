# termcolor

Set your terminal background color per directory, like `.editorconfig` for your terminal.

Place a `.termcolor` file anywhere in your project tree:

```ini
# https://github.com/orochi235/termcolor
background=#1a0a0a
```

When you `cd` into that directory (or any subdirectory), your terminal background changes. When you leave, it resets. The nearest `.termcolor` walking up from `$PWD` wins.

Named colors from the [X11 rgb.txt](https://gitlab.freedesktop.org/xorg/app/rgb/-/raw/master/rgb.txt) list are supported in addition to hex values:

```ini
background=midnightblue
```

## Install

### Homebrew (recommended)

```zsh
brew tap orochi235/termcolor
brew install termcolor
```

Then add to your shell config:

**Zsh** (`~/.zshrc`):
```zsh
source "$(brew --prefix)/share/termcolor.sh"
precmd_functions+=(_termcolor_apply)
```

**Bash** (`~/.bashrc`):
```bash
source "$(brew --prefix)/share/termcolor.sh"
PROMPT_COMMAND="_termcolor_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
```

**Fish**:
```fish
cp (brew --prefix)/share/termcolor.fish ~/.config/fish/conf.d/termcolor.fish
```

### Manual

Clone the repo and source the script directly:

**Zsh**:
```zsh
source /path/to/termcolor.sh
precmd_functions+=(_termcolor_apply)
```

**Bash**:
```bash
source /path/to/termcolor.sh
PROMPT_COMMAND="_termcolor_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
```

**Fish**: copy `termcolor.fish` to `~/.config/fish/conf.d/termcolor.fish`.

## CLI

```
termcolor              # print the current directory's background color
termcolor set <color>  # create or update .termcolor in the current directory
termcolor where        # print the path to the controlling .termcolor file
```

## Terminal support

Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.
