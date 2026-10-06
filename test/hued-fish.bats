#!/usr/bin/env bats

HUED_FISH="$BATS_TEST_DIRNAME/../hued.fish"

ESC=$'\e'
BEL=$'\a'
BG_RESET="${ESC}]111;${BEL}"
FG_RESET="${ESC}]110;${BEL}"

setup() {
  command -v fish >/dev/null || skip "fish not installed"
  WORK="$(mktemp -d)"
  export XDG_CACHE_HOME="$WORK/.cache"
  cd "$WORK"
}

teardown() {
  [ -z "${WORK:-}" ] || rm -rf "$WORK"
}

# Run _hued_apply in a fresh fish process, optionally with env vars.
# Usage: fish_apply [VAR=value ...]
fish_apply() {
  env "$@" fish -c "source $HUED_FISH; _hued_apply"
}

# --- .hued file behavior ---

@test "no .hued, no env: resets both channels" {
  run fish_apply
  [ "$status" -eq 0 ]
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued bg only: applies bg, resets fg" {
  printf "background=#1a0a0a\n" > .hued
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued bg+fg: applies both" {
  printf "background=#1a0a0a\nforeground=#c8ff59\n" > .hued
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:c8/ff/59${BEL}"* ]]
}

@test ".hued with inline name comment: applies hex" {
  printf "background=#1a0a0a  # something\n" > .hued
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
}

# --- env var overrides ---

@test "env bg only: overrides file bg, file fg still used" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run fish_apply HUED_BACKGROUND="#ff0000"
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test "env both: ignores file entirely" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run fish_apply HUED_BACKGROUND="#ff0000" HUED_FOREGROUND="#00ff00"
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:00/ff/00${BEL}"* ]]
}

@test "env without file: applies env values" {
  run fish_apply HUED_BACKGROUND="#ff0000"
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env then unset: falls back to reset" {
  printf "background=#000000\n" > .hued
  run fish -c "
    set -gx HUED_BACKGROUND '#ff0000'
    source $HUED_FISH
    _hued_apply
    set -e HUED_BACKGROUND
    rm .hued
    _hued_apply
  "
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env accepts named colors" {
  run fish_apply HUED_BACKGROUND="midnightblue"
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

@test "env is case-insensitive" {
  run fish_apply HUED_BACKGROUND="MIDNIGHTBLUE"
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

# --- HUED_LOOKUP_PREFER_XKCD ---

@test "HUED_LOOKUP_PREFER_XKCD prefers the xkcd value for a shared name" {
  printf "background=red\n" > .hued
  run fish_apply HUED_LOOKUP_PREFER_XKCD=1
  [[ "$output" == *"${ESC}]11;rgb:e5/00/00${BEL}"* ]]
}

@test "without HUED_LOOKUP_PREFER_XKCD a shared name resolves to CSS" {
  printf "background=red\n" > .hued
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
}

@test "HUED_LOOKUP_PREFER_XKCD: off values are off (0 included)" {
  printf "background=red\n" > .hued
  for off in "" 0 false no off n FALSE No OFF N; do
    run fish_apply HUED_LOOKUP_PREFER_XKCD="$off"
    [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]] || {
      echo "HUED_LOOKUP_PREFER_XKCD=$off did not resolve red to CSS"; return 1; }
  done
}

@test "HUED_LOOKUP_PREFER_XKCD: an xkcd-only name resolves the same either way" {
  printf "background=emerald\n" > .hued
  run fish_apply HUED_LOOKUP_PREFER_XKCD=1
  [[ "$output" == *"${ESC}]11;rgb:01/a0/49${BEL}"* ]]
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:01/a0/49${BEL}"* ]]
}

# --- name normalization ---

@test "a hyphenated name in .hued resolves" {
  printf "background=baby-blue\n" > .hued
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:a2/cf/fe${BEL}"* ]]
}

@test "a hyphenated HUED_BACKGROUND resolves" {
  run fish_apply HUED_BACKGROUND="baby-blue"
  [[ "$output" == *"${ESC}]11;rgb:a2/cf/fe${BEL}"* ]]
}

@test "a name with regex metacharacters resolves to nothing" {
  printf "background=.*\n" > .hued
  run fish_apply
  [[ "$output" != *"${ESC}]11;rgb:"* ]]
}

# --- 'none' sentinel ---

@test "env bg=none: resets bg even when file sets it" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run fish_apply HUED_BACKGROUND="none"
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test ".hued bg=none: resets bg, ignoring parent" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  mkdir sub
  printf "background=none\n" > sub/.hued
  cd sub
  run fish_apply
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env none is case-insensitive" {
  run fish_apply HUED_BACKGROUND="None"
  [[ "$output" == *"$BG_RESET"* ]]
}

@test ".hued with a key twice: the later line wins" {
  printf "background=#1a0a0a\nbackground=#c8ff59\n" > .hued
  run fish_apply
  [[ "$output" == *"${ESC}]11;rgb:c8/ff/59${BEL}"* ]]
}
