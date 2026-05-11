#!/usr/bin/env bats

HUED_FISH="$BATS_TEST_DIRNAME/../hued.fish"

ESC=$'\e'
BEL=$'\a'
BG_RESET="${ESC}]111;${BEL}"
FG_RESET="${ESC}]110;${BEL}"

setup() {
  command -v fish >/dev/null || skip "fish not installed"
  TMPDIR="$(mktemp -d)"
  cd "$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR"
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
