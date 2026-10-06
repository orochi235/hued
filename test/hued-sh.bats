#!/usr/bin/env bats

HUED_SH="$BATS_TEST_DIRNAME/../hued.sh"

# Escape sequence fragments — make assertions readable
ESC=$'\e'
BEL=$'\a'
BG_RESET="${ESC}]111;${BEL}"
FG_RESET="${ESC}]110;${BEL}"

setup() {
  WORK="$(mktemp -d)"
  export XDG_CACHE_HOME="$WORK/.cache"
  cd "$WORK"
  unset HUED_BACKGROUND HUED_FOREGROUND HUED_LOOKUP_PREFER_XKCD
  # shellcheck disable=SC1090
  source "$HUED_SH"
}

teardown() {
  [ -z "${WORK:-}" ] || rm -rf "$WORK"
}

# --- .hued file behavior ---

@test "no .hued, no env: resets both channels" {
  run _hued_apply_fallback
  [ "$status" -eq 0 ]
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued bg only: applies bg, resets fg" {
  printf "background=#1a0a0a\n" > .hued
  run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued bg+fg: applies both" {
  printf "background=#1a0a0a\nforeground=#c8ff59\n" > .hued
  run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:c8/ff/59${BEL}"* ]]
}

@test ".hued with inline name comment: applies hex" {
  printf "background=#1a0a0a  # something\n" > .hued
  run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
}

# --- env var overrides ---

@test "env bg only: overrides file bg, file fg still used" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_BACKGROUND="#ff0000" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test "env both: ignores file entirely" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_BACKGROUND="#ff0000" HUED_FOREGROUND="#00ff00" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:00/ff/00${BEL}"* ]]
}

@test "env without file: applies env values" {
  HUED_BACKGROUND="#ff0000" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env unset (simulated): re-running falls back to reset" {
  printf "background=#000000\n" > .hued
  HUED_BACKGROUND="#ff0000" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  rm .hued
  run _hued_apply_fallback
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env accepts named colors" {
  HUED_BACKGROUND="midnightblue" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

@test "env is case-insensitive" {
  HUED_BACKGROUND="MIDNIGHTBLUE" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

# --- 'none' sentinel ---

@test "env bg=none: resets bg even when file sets it" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_BACKGROUND="none" run _hued_apply_fallback
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test ".hued bg=none: resets bg, ignoring parent" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  mkdir sub
  printf "background=none\n" > sub/.hued
  cd sub
  run _hued_apply_fallback
  [[ "$output" == *"$BG_RESET"* ]]
  # parent's fg is not inherited because the closer .hued breaks the walk
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env none is case-insensitive" {
  HUED_BACKGROUND="None" run _hued_apply_fallback
  [[ "$output" == *"$BG_RESET"* ]]
}

# --- HUED_LOOKUP_PREFER_XKCD ---

@test "HUED_LOOKUP_PREFER_XKCD prefers the xkcd value for a shared name" {
  printf "background=red\n" > .hued
  HUED_LOOKUP_PREFER_XKCD=1 run _hued_apply_fallback
  [ "$status" -eq 0 ]
  [[ "$output" == *"${ESC}]11;rgb:e5/00/00${BEL}"* ]]
}

@test "without HUED_LOOKUP_PREFER_XKCD a shared name resolves to CSS" {
  printf "background=red\n" > .hued
  run _hued_apply_fallback
  [ "$status" -eq 0 ]
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
}

@test "HUED_LOOKUP_PREFER_XKCD: off values are off (0 included)" {
  printf "background=red\n" > .hued
  for off in "" 0 false no off n FALSE No OFF N; do
    HUED_LOOKUP_PREFER_XKCD="$off" run _hued_apply_fallback
    [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]] || {
      echo "HUED_LOOKUP_PREFER_XKCD=$off did not resolve red to CSS"; return 1; }
  done
}

@test "HUED_LOOKUP_PREFER_XKCD: an xkcd-only name resolves the same either way" {
  printf "background=emerald\n" > .hued
  HUED_LOOKUP_PREFER_XKCD=1 run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:01/a0/49${BEL}"* ]]
  run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:01/a0/49${BEL}"* ]]
}

# --- name normalization ---

@test "a hyphenated name in .hued resolves" {
  printf "background=baby-blue\n" > .hued
  run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:a2/cf/fe${BEL}"* ]]
}

@test "a hyphenated HUED_BACKGROUND resolves" {
  HUED_BACKGROUND="baby-blue" run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:a2/cf/fe${BEL}"* ]]
}

@test "a name with regex metacharacters resolves to nothing" {
  printf "background=.*\n" > .hued
  run _hued_apply_fallback
  [[ "$output" != *"${ESC}]11;rgb:"* ]]
}

# --- dispatcher: delegate vs fallback ---

@test "_hued_apply delegates to 'hued apply' when hued is on PATH" {
  hued() { echo "DELEGATED $*"; }
  output="$(_hued_apply)"
  [[ "$output" == "DELEGATED apply" ]]
}

@test "_hued_apply uses the inline fallback when hued is unavailable" {
  # Shadow the 'command' builtin so 'command -v hued' reports not-found.
  command() { return 1; }
  output="$(_hued_apply)"
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued with a key twice: the later line wins" {
  printf "background=#1a0a0a\nbackground=#c8ff59\n" > .hued
  run _hued_apply_fallback
  [[ "$output" == *"${ESC}]11;rgb:c8/ff/59${BEL}"* ]]
}
