# hued

Declarative per-directory terminal colors. A shell hook (`_hued_apply`, wired
via `precmd_functions` in zsh / `PROMPT_COMMAND` in bash / `conf.d` in fish)
walks up from `$PWD` to find the nearest `.hued` file and emits OSC 10/11
escapes to set foreground/background. `HUED_BACKGROUND` / `HUED_FOREGROUND` env
vars override the file (lets direnv/mise drive colors).

The `hued` CLI handles get/set/mod/pack/unpack/resolve/picker. Color resolution
shells out to `pastel` for transforms; named X11 colors come from
`hued-names.sh`. Interactive picker (`hued -i`) is stdlib-only Python.

Distribution: Homebrew tap (`orochi235/hued`) plus manual install. Must stay
**platform-agnostic**.

Tests live in `test/` (bats) and `tests/picker/` (pytest). Run with `make` or
the individual `bats test/*.bats` / `pytest` invocations.
