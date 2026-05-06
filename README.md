# termcolor

Set your terminal background color per directory, like `.editorconfig` for your terminal.

Place a `.termcolor` file anywhere in your project tree:

```ini
background=#1a0a0a
```

When you `cd` into that directory (or any subdirectory), your terminal background changes. When you leave, it resets. The nearest `.termcolor` walking up from `$PWD` wins.

## Install

### Zsh

```zsh
source /path/to/termcolor.sh
precmd_functions+=(_termcolor_apply)
```

### Bash

```bash
source /path/to/termcolor.sh
PROMPT_COMMAND="_termcolor_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
```

### Fish

Copy `termcolor.fish` to `~/.config/fish/conf.d/termcolor.fish`.

## Terminal support

Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.
