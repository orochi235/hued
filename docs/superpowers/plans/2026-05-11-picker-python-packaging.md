# Picker Python Port — Phase 5: Packaging & Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing TypeScript-compiled picker (`bin/hued-pick`, currently a compiled JS artifact on `feature/interactive-mode` only — it does NOT exist on `main`) with the new Python implementation, end-to-end. Add `bin/hued-pick` as a shell shim. Wire `bin/hued -i` to invoke it. Update the Homebrew formula to install the Python picker package. Update the README. Remove all Node-era artifacts. Cut a v3.0.0 release.

**Architecture:** The Python picker package lives at `src/picker/` in the repo and is installed to `libexec/hued/picker/` by brew. `bin/hued-pick` is a shell script that detects whether it is running from the source tree or a brew prefix and sets `PYTHONPATH` accordingly before executing `python3 -m picker`. `bin/hued` gains a `-i` / `--interactive` flag that delegates to `bin/hued-pick`, preserving the output-file dance from the `feature/interactive-mode` prototype (read current colors from the nearest `.hued` file, pass them to the picker, write results back). The Homebrew formula gets `depends_on "python@3.12"` and a `libexec` install step; Node deps are dropped entirely.

**Tech Stack:** bash (shim + CLI), Python 3.9+ stdlib (picker), Ruby (formula), bats (shell tests).

**Branch strategy:** Cut `feature/picker-packaging` from `main` AFTER Phase 4 (`feature/picker-app`) merges. All hued-repo changes land on `feature/picker-packaging`. The Homebrew tap (`~/src/homebrew-termcolor/`) is edited directly on its own default branch (no PR needed for a single-maintainer tap).

---

## Preflight findings (verified before this plan was written)

The implementer should re-verify these at branch-cut time, but they are captured here so task code is concrete rather than hand-wavy.

**`bin/hued` on `main`:**
- Does NOT have a `-i` / `--interactive` flag.
- The `case` statement ends with a `*)` catch-all that prints usage and exits 1.
- Usage line: `hued [where | set [bg|fg] <color> | pack [<dir>] [-o <file>] | unpack <file> [--force]]`.
- Uses `_HUED_DIR` (the repo/install prefix, one level up from `bin/`), sets `python3` inline for `pack`/`unpack`.
- Already uses `python3` for inline scripts in `pack` and `unpack` subcommands — no Node dependency on `main`.

**`bin/hued-pick` on `main`:** Does not exist. It only exists on `feature/interactive-mode` as a compiled JS bundle (`#!/usr/bin/env node`).

**`bin/hued` on `feature/interactive-mode`:** Has a `-i|--interactive)` case (lines 149-184). It checks for `node`, finds `hued-pick`, reads current bg/fg from `.hued`, passes `--bg`/`--fg`/`--live`/`--output` flags to `node "$_picker"`, then reads the output file and calls `_hued_set_key` for each line. This is the exact flow to preserve — only the `node "$_picker"` invocation changes to the shim.

**Node artifacts on `main`:** `node_modules/` exists (115 entries) but is untracked (in `.gitignore`). `package.json`, `package-lock.json`, `build.mjs`, `tsconfig.json` are tracked on `feature/interactive-mode` only — none exist on `main`. So Task 7 (cleanup) only needs to handle the untracked `node_modules/` directory.

**`src/picker/lib/` on `main`:** Does not exist. It exists on `feature/interactive-mode` (`lib/colors.ts`, `lib/names.ts`, `lib/osc.ts`). After Phase 4 merges to `main`, `src/picker/` will contain: `__init__.py`, `__main__.py`, `app.py`, `colors.py`, `components/`, `frame.py`, `keys.py`, `names.py`, `term.py`.

**Homebrew formula (`~/src/homebrew-termcolor/Formula/hued.rb`):**
- Currently installs: `bin/hued`, `hued.sh`, `hued-names.sh`, `hued.fish`, and all completions.
- Does NOT install `bin/hued-pick` (it's not shipped in any release).
- No Python dep (already uses Python incidentally via `bin/hued pack/unpack`, but not declared).
- Latest tag: v2.5.0.

**`src/picker/__main__.py` entry point (Phase 4):** After Phase 4, `src/picker/__main__.py` calls `app.main()` when `--app` is passed. `app.main()` accepts `--bg`, `--fg`, `--live`, `--output` flags. After Phase 5, `python3 -m picker` (with PYTHONPATH set to the package root) should invoke the picker directly — so `__main__.py` needs to call `app.main()` unconditionally (or by default), not just when `--app` is passed.

---

## Task 1: Branch + preflight state capture

**Files:** none (read-only inspection)

- [ ] **Step 1: Create branch**

```bash
cd /Users/mike/src/hued
git checkout main && git pull --ff-only
git checkout -b feature/picker-packaging
```

- [ ] **Step 2: Capture preflight state to a reference file**

```bash
{
  echo "=== bin/hued (case statement tail) ==="
  tail -40 bin/hued
  echo ""
  echo "=== bin/hued-pick (does it exist?) ==="
  ls -la bin/hued-pick 2>/dev/null || echo "bin/hued-pick does not exist on main (expected)"
  echo ""
  echo "=== src/picker/ tree ==="
  find src/picker -type f | sort
  echo ""
  echo "=== Untracked Node artifacts ==="
  ls -d node_modules 2>/dev/null && echo "node_modules/ present (untracked)" || echo "node_modules/ absent"
  echo ""
  echo "=== git status ==="
  git status --short
} > /tmp/phase5-preflight.txt
cat /tmp/phase5-preflight.txt
```

Expected: `bin/hued-pick does not exist on main (expected)`. `src/picker/` shows `app.py` (from Phase 4). `node_modules/` is present but untracked. If any of these differ from expectations, stop and re-read the plan before proceeding.

---

## Task 2: `bin/hued-pick` shim

**Files:**
- Create: `bin/hued-pick`

- [ ] **Step 1: Write the shim**

Create `bin/hued-pick`:

```bash
#!/usr/bin/env bash
# hued-pick — launch the interactive color picker (Python implementation)
#
# PYTHONPATH resolution order:
#   1. <prefix>/libexec/hued/  — brew-installed location (picker/ is a subdir)
#   2. <repo-root>/src/         — source-tree location (picker/ is a subdir of src/)
#   3. Error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -d "$PREFIX_DIR/libexec/hued/picker" ]]; then
  # Installed via brew: libexec/hued/picker/__init__.py exists
  export PYTHONPATH="$PREFIX_DIR/libexec/hued${PYTHONPATH:+:$PYTHONPATH}"
elif [[ -d "$PREFIX_DIR/src/picker" ]]; then
  # Source tree: src/picker/__init__.py exists
  export PYTHONPATH="$PREFIX_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
else
  printf 'hued-pick: cannot find picker package\n' >&2
  printf '  looked for: %s/libexec/hued/picker\n' "$PREFIX_DIR" >&2
  printf '              %s/src/picker\n' "$PREFIX_DIR" >&2
  exit 1
fi

exec python3 -m picker "$@"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x bin/hued-pick
```

- [ ] **Step 3: Smoke-test the shim from the source tree**

```bash
# Must print the picker's help text and exit 0
bin/hued-pick --help
```

Expected: the picker's help/usage text (from `app.main()` argparse). Exit code 0.

If `app.main()` does not yet implement `--help`, at minimum the invocation must not produce a traceback — it may exit non-zero with "unrecognized argument" which is acceptable at this stage. The full `--help` behavior is covered by Phase 4.

- [ ] **Step 4: Confirm PYTHONPATH detection in source tree**

```bash
# Confirm the right branch fires: src/picker must exist, libexec must not
ls src/picker/__init__.py   # must print the path
ls "$PREFIX_DIR/libexec/hued/picker" 2>/dev/null && echo "libexec present (unexpected)" || echo "libexec absent (expected)"
```

- [ ] **Step 5: Commit**

```bash
git add bin/hued-pick
git commit -m "feat: add bin/hued-pick shell shim (Python picker)"
```

---

## Task 3: `bin/hued` — wire `-i` / `--interactive` flag

The `feature/interactive-mode` branch already has a working `-i` handler. We port it to `main`'s `bin/hued`, replacing the `node "$_picker"` call with `"$_picker"` (the shim handles the interpreter).

**Files:**
- Modify: `bin/hued`

- [ ] **Step 1: Confirm current case statement structure**

```bash
grep -n 'case\|esac\|\*)\|Usage:' bin/hued
```

Expected output shows the `case "${1:-}" in` near line 55 and `esac` at the last line, with the `*)` catch-all printing usage.

- [ ] **Step 2: Edit `bin/hued` — add the `-i` case and update usage**

Insert the new case branch before the `*)` catch-all, and extend the usage string. The diff is:

In `bin/hued`, replace:

```bash
  *)
    echo "Usage: hued [where | set [bg|fg] <color> | pack [<dir>] [-o <file>] | unpack <file> [--force]]" >&2
    exit 1
    ;;
esac
```

with:

```bash
  -i|--interactive)
    _picker="$(dirname "$0")/hued-pick"
    if [[ ! -f "$_picker" ]]; then
      echo "hued -i: hued-pick not found at $_picker" >&2
      exit 1
    fi
    _current_bg=""
    _current_fg=""
    if _file=$(_hued_find 2>/dev/null); then
      _raw_bg=$(grep -m1 '^background=' "$_file" | cut -d= -f2 | tr -d '[:space:]')
      _raw_fg=$(grep -m1 '^foreground=' "$_file" | cut -d= -f2 | tr -d '[:space:]')
      [[ -n "$_raw_bg" ]] && _current_bg=$(_hued_normalize_color "$_raw_bg")
      [[ -n "$_raw_fg" ]] && _current_fg=$(_hued_normalize_color "$_raw_fg")
    fi
    _live_flag=""
    for _arg in "$@"; do [[ "$_arg" == "--live" ]] && _live_flag="--live" && break; done
    _tmpfile=$(mktemp)
    "$_picker" \
      ${_current_bg:+--bg "$_current_bg"} \
      ${_current_fg:+--fg "$_current_fg"} \
      ${_live_flag:+"$_live_flag"} --output "$_tmpfile" || { rm -f "$_tmpfile"; exit 0; }
    while IFS='=' read -r _key _value; do
      case "$_key" in
        background) _hued_set_key "background" "$_value" ;;
        foreground) _hued_set_key "foreground" "$_value" ;;
      esac
    done < "$_tmpfile"
    rm -f "$_tmpfile"
    ;;

  *)
    echo "Usage: hued [where | set [bg|fg] <color> | pack [<dir>] [-o <file>] | unpack <file> [--force] | -i [--live]]" >&2
    exit 1
    ;;
esac
```

- [ ] **Step 3: Verify the edit is clean**

```bash
bash -n bin/hued && echo "syntax ok"
```

Expected: `syntax ok`.

- [ ] **Step 4: Confirm the new case appears**

```bash
grep -n 'interactive\|hued-pick\|--live' bin/hued
```

Expected: three matches — the case label, the shim path construction, and the live-flag loop.

- [ ] **Step 5: Commit**

```bash
git add bin/hued
git commit -m "feat: wire bin/hued -i / --interactive to Python picker shim"
```

---

## Task 4: Update `src/picker/__main__.py` entry point

After Phase 4, `__main__.py` only calls `app.main()` when `--app` is passed on the command line. The shim runs `python3 -m picker "$@"` which invokes `__main__.py`. We need `__main__.py` to route to `app.main()` by default (the `--app` flag path can remain for backward compatibility).

**Files:**
- Modify: `src/picker/__main__.py`

- [ ] **Step 1: Read current `__main__.py`**

```bash
cat src/picker/__main__.py
```

Identify the `if "--app" in sys.argv` branch.

- [ ] **Step 2: Make `app.main()` the default**

Replace the routing logic so `app.main()` runs when `--app` is in argv OR when `__main__.py` is invoked directly (i.e., always, unless the legacy Phase 2 smoke path is explicitly requested with `--smoke`). The replacement:

```python
"""picker — interactive terminal color picker.

Run:
  python3 -m picker [--bg <hex>] [--fg <hex>] [--live] [--output <file>]
  python3 -m picker --help

The --smoke flag invokes the Phase 2 frame smoke test (development only).
"""
import sys


def main() -> int:
    if "--smoke" in sys.argv:
        # Phase 2 smoke test path — development only, not invoked by the shim
        from src.picker import term as t
        from src.picker.colors import hex_to_rgb
        from src.picker.frame import Frame
        from src.picker.names import NAMED_COLORS

        first_name = next(iter(NAMED_COLORS))
        first_hex = NAMED_COLORS[first_name]

        sys.stdout.write(t.enter_alt_screen())
        sys.stdout.write(t.hide_cursor())
        sys.stdout.write(t.clear_screen())
        sys.stdout.flush()
        t.osc_bg(first_hex)

        def on_resize(cols: int, rows: int) -> None:
            sys.stdout.write(t.clear_screen())
            _smoke_render(cols, rows, first_name, first_hex)

        t.install_resize_handler(on_resize)

        try:
            cols, rows = t.get_size()
            _smoke_render(cols, rows, first_name, first_hex)
            with t.raw_mode():
                event = t.read_key()
        finally:
            t.uninstall_resize_handler()
            t.osc_reset_bg()
            t.osc_reset_fg()
            sys.stdout.write(t.show_cursor())
            sys.stdout.write(t.exit_alt_screen())
            sys.stdout.flush()

        print(f"got: key={event.key.name} char={event.char!r} "
              f"shift={event.shift} ctrl={event.ctrl}")
        return 0

    # Default: launch the interactive picker (Phase 4 app)
    from src.picker.app import main as app_main
    return app_main()


def _smoke_render(cols: int, rows: int, first_name: str, first_hex: str) -> None:
    from src.picker.colors import hex_to_rgb
    from src.picker.colors import RGB
    from src.picker.frame import Frame
    from src.picker import term as t

    SWATCH_HEXES = ["#ff5555", "#ffaa55", "#ffff55", "#55ff55",
                    "#55ffff", "#5555ff", "#aa55ff", "#ff55aa"]
    f = Frame(cols, rows)
    f.box(0, 0, cols, rows, fg=RGB(128, 128, 128))
    for i, hex_v in enumerate(SWATCH_HEXES):
        rgb = hex_to_rgb(hex_v)
        f.fill(1, 1 + i * 8, w=8, h=1, char=" ", bg=rgb)
    f.put_str(3, 2, f"terminal bg: {first_name} ({first_hex})")
    f.put_str(5, 2, "press any key to exit (try arrow keys, shift+arrow, ctrl-c)")
    f.flush()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Verify the smoke path still works**

```bash
python3 -m src.picker --smoke
```

Expected: the Phase 2 bordered screen with swatches appears; press any key to exit cleanly.

- [ ] **Step 4: Verify the default path routes to app.main()**

```bash
python3 -m src.picker --help
```

Expected: argparse help from `app.main()`, not a traceback.

- [ ] **Step 5: Commit**

```bash
git add src/picker/__main__.py
git commit -m "feat(picker): make app.main() the default __main__ entry point"
```

---

## Task 5: bats tests for the shim and CLI flag

**Files:**
- Create: `test/picker_shim.bats`

- [ ] **Step 1: Create the test file**

Create `test/picker_shim.bats`:

```bash
#!/usr/bin/env bats

# ---------------------------------------------------------------------------
# Tests for bin/hued-pick shim and bin/hued -i wiring.
#
# These tests do NOT start the picker interactively (that requires a TTY).
# They verify the shim's path-resolution logic, Python invocability, and
# the CLI flag wiring, all without a real terminal.
# ---------------------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HUED_PICK="$REPO_ROOT/bin/hued-pick"
HUED="$REPO_ROOT/bin/hued"

@test "bin/hued-pick exists and is executable" {
  [[ -x "$HUED_PICK" ]]
}

@test "bin/hued-pick shebang is bash" {
  head -1 "$HUED_PICK" | grep -q 'env bash'
}

@test "bin/hued-pick --help exits 0 and mentions picker" {
  run "$HUED_PICK" --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ [Pp]icker ]]
}

@test "bin/hued-pick resolves src/picker in source tree" {
  # Confirm PYTHONPATH resolution prints no 'cannot find picker' error
  run "$HUED_PICK" --help 2>&1
  [[ ! "$output" =~ "cannot find picker package" ]]
}

@test "bin/hued -i flag is recognized (no TTY exits nonzero, not 'unknown command')" {
  # Without a TTY the picker will fail (can't enter raw mode), but it must NOT
  # print the 'Usage:' line from the catch-all — that would mean -i is unrecognized.
  run "$HUED" -i </dev/null 2>&1 || true
  [[ ! "$output" =~ "Usage: hued" ]]
}

@test "bin/hued shows updated usage including -i" {
  run "$HUED" --no-such-flag 2>&1 || true
  [[ "$output" =~ "\-i" ]]
}

@test "bin/hued-pick fails gracefully when python3 is absent" {
  # Temporarily shadow python3 with a no-op that exits 127.
  # We verify the shim itself doesn't crash before exec.
  run bash -c '
    mkdir -p /tmp/hued_test_bin
    printf "#!/bin/sh\nexit 127\n" > /tmp/hued_test_bin/python3
    chmod +x /tmp/hued_test_bin/python3
    PATH=/tmp/hued_test_bin:$PATH '"$HUED_PICK"' --help
    rm -rf /tmp/hued_test_bin
  '
  # Exit code should be 127 (python3 not found), not 1 (shim logic error)
  [ "$status" -eq 127 ]
}
```

- [ ] **Step 2: Run tests**

```bash
bats test/picker_shim.bats
```

Expected: all 7 tests pass. If `bats` is not installed: `brew install bats-core`.

- [ ] **Step 3: Commit**

```bash
git add test/picker_shim.bats
git commit -m "test: bats tests for bin/hued-pick shim and -i CLI flag"
```

---

## Task 6: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README**

```bash
cat README.md
```

Identify the CLI section (lines 67-79 in the current file) and the Terminal support section at the bottom.

- [ ] **Step 2: Edit README.md**

Make the following changes to `README.md`:

**a) In the CLI table**, add the `-i` row after `hued unpack`:

Replace:

```
hued unpack <file> [--force]  # restore .hued files from a JSON export
```

with:

```
hued unpack <file> [--force]  # restore .hued files from a JSON export
hued -i [--live]              # open interactive color picker
```

**b) Add a new `## Interactive picker` section** after the CLI section (before `## Environment variables`):

```markdown
## Interactive picker

`hued -i` opens a fullscreen terminal color picker. Use the arrow keys to
adjust colors by channel, tab between panes, and press Enter to confirm.
The selected colors are written to the nearest `.hued` file.

Pass `--live` to apply colors immediately as you move sliders:

```zsh
hued -i --live
```

**Requirements:** Python 3.9 or later. No Node.js required.

The picker is implemented in stdlib-only Python and ships as part of the hued
package. Homebrew installations include Python 3.12 as a dependency.
```

**c) Update the Terminal support section** — append one sentence:

Replace:

```
Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.
```

with:

```
Uses the `\e]11;rgb:RR/GG/BB\a` OSC escape sequence, supported by iTerm2, Terminal.app, Alacritty, Kitty, WezTerm, and most modern terminals.

Node.js is no longer required as of v3.0.0. The picker is now a stdlib-only Python application.
```

- [ ] **Step 3: Verify the README renders**

```bash
# Quick sanity: no stray triple-backtick mismatches
python3 -c "
import re, pathlib
text = pathlib.Path('README.md').read_text()
opens = text.count('\`\`\`')
assert opens % 2 == 0, f'Odd number of triple-backtick fences: {opens}'
print('fence count ok:', opens)
"
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document interactive picker, Python requirement, remove Node note"
```

---

## Task 7: Homebrew formula update

**Repo:** `~/src/homebrew-termcolor/` (default branch, edit in-place — this is a single-maintainer tap with no PR process).

**Files:**
- Modify: `~/src/homebrew-termcolor/Formula/hued.rb`

The goal: add `depends_on "python@3.12"`, install the picker package to `libexec/hued/`, install `bin/hued-pick`, update the URL/SHA to v3.0.0 (SHA is a placeholder until the tag is pushed in Task 8).

- [ ] **Step 1: Read the current formula**

```bash
cat ~/src/homebrew-termcolor/Formula/hued.rb
```

Confirm: URL is v2.5.0, no Python dep, no `bin/hued-pick` install, no `libexec` install.

- [ ] **Step 2: Replace the formula**

Write `~/src/homebrew-termcolor/Formula/hued.rb`:

```ruby
class Hued < Formula
  desc "Change terminal colors declaratively by directory"
  homepage "https://github.com/orochi235/hued"
  url "https://github.com/orochi235/hued/archive/refs/tags/v3.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256_FILL_IN_AFTER_TAG_PUSH"
  license "MIT"

  depends_on "python@3.12"

  def install
    bin.install "bin/hued"
    bin.install "bin/hued-pick"
    share.install "hued.sh"
    share.install "hued-names.sh"
    share.install "hued.fish"
    bash_completion.install "completions/hued.bash"
    zsh_completion.install "completions/_hued"
    fish_completion.install "completions/hued.fish"
    (libexec/"hued").install "src/picker"
  end

  def caveats
    <<~EOS
      Add to your shell config:

      Zsh (~/.zshrc):
        source #{share}/hued.sh
        precmd_functions+=(_hued_apply)

      Bash (~/.bashrc):
        source #{share}/hued.sh
        PROMPT_COMMAND="_hued_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"

      Fish:
        cp #{share}/hued.fish ~/.config/fish/conf.d/hued.fish
    EOS
  end
end
```

**Note on the `libexec` line:** `(libexec/"hued").install "src/picker"` installs the `src/picker/` directory tree to `<prefix>/libexec/hued/picker/`. The shim checks for `<prefix>/libexec/hued/picker/__init__.py` and sets `PYTHONPATH="<prefix>/libexec/hued"` — so `python3 -m picker` resolves correctly.

**Note on `sha256`:** The literal string `PLACEHOLDER_SHA256_FILL_IN_AFTER_TAG_PUSH` is intentional. Task 8 fills in the real value after `git push origin v3.0.0`.

- [ ] **Step 3: Verify Ruby syntax**

```bash
ruby -e "load '#{Dir.home}/src/homebrew-termcolor/Formula/hued.rb'" 2>&1 | head -5 || true
```

If ruby is available, no output means no parse errors. Alternatively:

```bash
brew style ~/src/homebrew-termcolor/Formula/hued.rb 2>&1 | head -10 || true
```

Minor Homebrew style warnings (line length) are acceptable at this stage.

- [ ] **Step 4: Commit the formula to the tap repo**

```bash
cd ~/src/homebrew-termcolor
git add Formula/hued.rb
git commit -m "feat: v3.0.0 — Python picker, drop Node dep, add libexec install"
```

(Do NOT push yet — push happens in Task 8 after the SHA is filled in.)

---

## Task 8: Remove Node-era artifacts from the hued repo

On `main`, the only Node-era artifact present is the untracked `node_modules/` directory. `package.json`, `package-lock.json`, `build.mjs`, `tsconfig.json`, and `vitest.config.ts` do not exist on `main` (they are on `feature/interactive-mode` only). `bin/hued-pick` (the JS file) also does not exist on `main` — Phase 5 added the Python shim in Task 2.

- [ ] **Step 1: Confirm node_modules is untracked**

```bash
cd /Users/mike/src/hued
git ls-files node_modules | head -5
```

Expected: no output (untracked).

- [ ] **Step 2: Remove node_modules**

```bash
rm -rf node_modules
```

- [ ] **Step 3: Confirm nothing else to clean**

```bash
git status --short
```

Expected: only the changes from Tasks 2-6 (new `bin/hued-pick`, modified `bin/hued`, modified `src/picker/__main__.py`, modified `README.md`, new `test/picker_shim.bats`). No stray `.ts` or `.js` files.

- [ ] **Step 4: Confirm `src/picker/lib/` does not exist on main**

```bash
ls src/picker/lib 2>/dev/null && echo "ERROR: lib/ exists and must be removed" || echo "src/picker/lib/ absent (expected)"
```

If `lib/` exists (it should not), remove it:

```bash
rm -rf src/picker/lib
git add -A src/picker/lib
```

- [ ] **Step 5: No additional commit needed for node_modules**

`node_modules/` is untracked and in `.gitignore` — deleting it requires no git action.

---

## Task 9: Tag v3.0.0 and update the formula SHA

This task is split into a hued-repo step and a tap-repo step. The implementer must run the brew formula validation manually (it cannot be automated in this environment).

- [ ] **Step 1: Final test run before tagging**

```bash
cd /Users/mike/src/hued
.venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -20
bats test/picker_shim.bats
bash -n bin/hued && echo "bin/hued syntax ok"
bash -n bin/hued-pick && echo "bin/hued-pick syntax ok"
```

All tests must pass. Fix any failures before proceeding.

- [ ] **Step 2: Merge `feature/picker-packaging` to `main`**

```bash
cd /Users/mike/src/hued
git checkout main
git merge --no-ff feature/picker-packaging -m "feat: Phase 5 — Python picker packaging, bin/hued -i, remove Node deps"
```

- [ ] **Step 3: Tag v3.0.0**

```bash
git tag -a v3.0.0 -m "v3.0.0 — Python picker replaces Node-based prototype"
```

- [ ] **Step 4: Push the tag**

```bash
git push origin main
git push origin v3.0.0
```

- [ ] **Step 5: Compute the release tarball SHA**

```bash
curl -sL https://github.com/orochi235/hued/archive/refs/tags/v3.0.0.tar.gz -o /tmp/v3.0.0.tar.gz
shasum -a 256 /tmp/v3.0.0.tar.gz
```

Copy the 64-character hex string printed by `shasum`.

- [ ] **Step 6: Update the formula SHA**

```bash
cd ~/src/homebrew-termcolor
# Replace the placeholder with the real SHA (paste yours in):
REAL_SHA="<paste 64-char sha256 here>"
sed -i '' "s/PLACEHOLDER_SHA256_FILL_IN_AFTER_TAG_PUSH/$REAL_SHA/" Formula/hued.rb
grep sha256 Formula/hued.rb   # confirm the replacement
```

- [ ] **Step 7: Commit and push the tap**

```bash
git add Formula/hued.rb
git commit -m "feat: update hued.rb sha256 for v3.0.0 release"
git push origin HEAD
```

---

## Verification before declaring Phase 5 done

Run this checklist locally:

- [ ] `bash -n bin/hued` — exit 0, no errors.
- [ ] `bash -n bin/hued-pick` — exit 0, no errors.
- [ ] `bin/hued-pick --help` — exits 0, prints picker usage.
- [ ] `bin/hued --no-such-flag 2>&1 | grep -q '\-i'` — usage line mentions `-i`.
- [ ] `.venv/bin/pytest tests/ -v` — all green.
- [ ] `bats test/picker_shim.bats` — all green.
- [ ] `ls node_modules 2>/dev/null || echo "gone"` — prints `gone`.
- [ ] `ls src/picker/lib 2>/dev/null || echo "gone"` — prints `gone`.
- [ ] `git log --oneline -8` — shows the merge commit and the Phase 5 task commits in sequence.
- [ ] `git tag v3.0.0` exists: `git tag | grep v3.0.0`.
- [ ] `grep sha256 ~/src/homebrew-termcolor/Formula/hued.rb` — does NOT contain `PLACEHOLDER`.
- [ ] `grep 'python@3.12' ~/src/homebrew-termcolor/Formula/hued.rb` — present.
- [ ] `grep 'libexec' ~/src/homebrew-termcolor/Formula/hued.rb` — present.

---

## Manual smoke test (human step — cannot be automated in this environment)

These steps must be run by the author in a live terminal after Task 9 completes. The agent doing the implementation documents them here for the author to run separately.

```bash
# 1. Uninstall any existing hued install
brew uninstall hued || true

# 2. Install from the updated tap formula using the source tree
#    (avoids waiting for GitHub to serve the tarball)
brew install --build-from-source ~/src/homebrew-termcolor/Formula/hued.rb

# 3. Confirm brew installed both binaries
ls -la "$(brew --prefix)/bin/hued"
ls -la "$(brew --prefix)/bin/hued-pick"

# 4. Confirm libexec layout
ls "$(brew --prefix)/libexec/hued/picker/__init__.py"

# 5. Test the shim points to the brew libexec tree (not the source tree)
PYTHONPATH="" "$(brew --prefix)/bin/hued-pick" --help

# 6. Run the interactive picker end-to-end
#    (requires a real terminal — do not run in a subprocess or CI)
hued -i --live
# Expected: the four-pane picker opens. Arrow keys move sliders.
# Press Enter on the fg step to confirm. The nearest .hued file is updated.
# Press Ctrl-C to cancel. Either way, the terminal background resets on exit.

# 7. Test without a .hued file present
cd /tmp
hued -i
# Expected: picker opens with default colors (black bg, white fg or similar).

# 8. Uninstall and reinstall from the GitHub tarball (after tag propagates)
brew uninstall hued
brew install orochi235/hued/hued
hued -i --help
```
