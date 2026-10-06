#!/usr/bin/env bats

HUED="$BATS_TEST_DIRNAME/../bin/hued"

ESC=$'\e'
BEL=$'\a'
BG_RESET="${ESC}]111;${BEL}"
FG_RESET="${ESC}]110;${BEL}"

setup() {
  WORK="$(mktemp -d)"
  export XDG_CACHE_HOME="$WORK/.cache"
  cd "$WORK"
  unset HUED_BACKGROUND HUED_FOREGROUND HUED_LOOKUP_PREFER_XKCD
  OUT="$WORK/tty.out"
}

teardown() {
  [ -z "${WORK:-}" ] || rm -rf "$WORK"
}

# --- hued apply: emit logic ---

@test "apply: emits bg escape from .hued to HUED_TTY" {
  printf "background=#1a0a0a\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "apply: emits both channels" {
  printf "background=#1a0a0a\nforeground=#c8ff59\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:c8/ff/59${BEL}"* ]]
}

@test "apply: resolves named colors via hued-names.sh" {
  printf "background=midnightblue\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

@test "apply: ignores inline name comment" {
  printf "background=#1a0a0a  # something\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
}

@test "apply: resolves named colors under share/ layout (brew install)" {
  # Homebrew installs bin/hued to <prefix>/bin and hued-names.sh to
  # <prefix>/share. _HUED_DIR resolves to <prefix>, so the names file must be
  # found under share/ too, not just at the repo root.
  mkdir -p prefix/bin prefix/share
  cp "$HUED" prefix/bin/hued
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" prefix/share/hued-names.sh
  printf 'background=goldenrod\n' > .hued
  HUED_TTY="$OUT" run "$PWD/prefix/bin/hued" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:da/a5/20${BEL}"* ]]
}

@test "apply: none resets the channel" {
  printf "background=none\nforeground=#ffffff\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test "apply: no .hued resets both channels" {
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "apply: HUED_BACKGROUND overrides the file" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_TTY="$OUT" HUED_BACKGROUND="#ff0000" run "$HUED" apply
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test "apply: walks up to the nearest .hued" {
  printf "background=#1a0a0a\n" > .hued
  mkdir -p sub/dir
  cd sub/dir
  HUED_TTY="$OUT" run "$HUED" apply
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
}

@test "apply: silent no-op when HUED_TTY target cannot be opened" {
  printf "background=#1a0a0a\n" > .hued
  HUED_TTY="$WORK/nope/tty.out" run "$HUED" apply
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ ! -e "$WORK/nope/tty.out" ]
}

# --- name normalization ---

@test "apply: resolves a hyphenated name from .hued" {
  printf "background=baby-blue\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:a2/cf/fe${BEL}"* ]]
}

@test "apply: resolves a hyphenated HUED_BACKGROUND" {
  HUED_TTY="$OUT" HUED_BACKGROUND="baby-blue" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:a2/cf/fe${BEL}"* ]]
}

@test "apply: a name with regex metacharacters resolves to nothing" {
  printf "background=.*\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" != *"${ESC}]11;rgb:"* ]]
}

# --- -x / HUED_LOOKUP_PREFER_XKCD on the apply path ---

@test "apply: -x prefers the xkcd value for a shared name" {
  printf "background=red\n" > .hued
  HUED_TTY="$OUT" run "$HUED" -x apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:e5/00/00${BEL}"* ]]
}

@test "apply: HUED_LOOKUP_PREFER_XKCD=1 prefers the xkcd value" {
  printf "background=red\n" > .hued
  HUED_TTY="$OUT" HUED_LOOKUP_PREFER_XKCD=1 run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:e5/00/00${BEL}"* ]]
}

@test "apply: without -x a shared name resolves to CSS" {
  printf "background=red\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
}

@test "apply: HUED_LOOKUP_PREFER_XKCD off values are off (0 included)" {
  printf "background=red\n" > .hued
  for off in "" 0 false no off n FALSE No OFF N; do
    : > "$OUT"
    HUED_TTY="$OUT" HUED_LOOKUP_PREFER_XKCD="$off" "$HUED" apply
    got="$(cat "$OUT")"
    [[ "$got" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]] || {
      echo "HUED_LOOKUP_PREFER_XKCD=$off did not resolve red to CSS"; return 1; }
  done
}

@test "apply: -x leaves an xkcd-only name unchanged" {
  printf "background=emerald\n" > .hued
  HUED_TTY="$OUT" run "$HUED" -x apply
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:01/a0/49${BEL}"* ]]
  : > "$OUT"
  HUED_TTY="$OUT" run "$HUED" apply
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:01/a0/49${BEL}"* ]]
}

# --- mutating commands repaint after writing ---

@test "set bg: repaints after writing" {
  HUED_TTY="$OUT" run "$HUED" set bg "#ff0000"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Set background to #ff0000"* ]]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
}

@test "set <color>: repaints after writing" {
  HUED_TTY="$OUT" run "$HUED" set "#00ff00"
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:00/ff/00${BEL}"* ]]
}

@test "mod: repaints after transforming" {
  if ! command -v pastel >/dev/null 2>&1; then skip "pastel not installed"; fi
  printf "background=#808080\n" > .hued
  HUED_TTY="$OUT" run "$HUED" mod bg lighten 50%
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:"* ]]
}

@test "unset: repaints after removing a channel" {
  printf "background=#1a0a0a\nforeground=#ffffff\n" > .hued
  HUED_TTY="$OUT" run "$HUED" unset bg
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test "fork: repaints after materializing inherited colors" {
  printf "background=#1a0a0a\n" > .hued
  mkdir sub
  cd sub
  HUED_TTY="$OUT" run "$HUED" fork
  [ "$status" -eq 0 ]
  [ -f .hued ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
}

@test "unpack: repaints after restoring" {
  printf '{"%s": {"background": "#1a0a0a"}}' "$WORK" > export.json
  HUED_TTY="$OUT" run "$HUED" unpack export.json --force
  [ "$status" -eq 0 ]
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
}

@test "apply: with a key twice, the later line wins" {
  printf "background=#1a0a0a\nbackground=#c8ff59\n" > .hued
  HUED_TTY="$OUT" run "$HUED" apply
  run cat "$OUT"
  [[ "$output" == *"${ESC}]11;rgb:c8/ff/59${BEL}"* ]]
}
