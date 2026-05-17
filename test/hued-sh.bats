#!/usr/bin/env bats

HUED_SH="$BATS_TEST_DIRNAME/../hued.sh"

# Escape sequence fragments — make assertions readable
ESC=$'\e'
BEL=$'\a'
BG_RESET="${ESC}]111;${BEL}"
FG_RESET="${ESC}]110;${BEL}"

setup() {
  TMPDIR="$(mktemp -d)"
  cd "$TMPDIR"
  unset HUED_BACKGROUND HUED_FOREGROUND
  # shellcheck disable=SC1090
  source "$HUED_SH"
}

teardown() {
  rm -rf "$TMPDIR"
}

# --- .hued file behavior ---

@test "no .hued, no env: resets both channels" {
  run _hued_apply
  [ "$status" -eq 0 ]
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued bg only: applies bg, resets fg" {
  printf "background=#1a0a0a\n" > .hued
  run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test ".hued bg+fg: applies both" {
  printf "background=#1a0a0a\nforeground=#c8ff59\n" > .hued
  run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:1a/0a/0a${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:c8/ff/59${BEL}"* ]]
}

# --- env var overrides ---

@test "env bg only: overrides file bg, file fg still used" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_BACKGROUND="#ff0000" run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test "env both: ignores file entirely" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_BACKGROUND="#ff0000" HUED_FOREGROUND="#00ff00" run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"${ESC}]10;rgb:00/ff/00${BEL}"* ]]
}

@test "env without file: applies env values" {
  HUED_BACKGROUND="#ff0000" run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env unset (simulated): re-running falls back to reset" {
  printf "background=#000000\n" > .hued
  HUED_BACKGROUND="#ff0000" run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:ff/00/00${BEL}"* ]]
  rm .hued
  run _hued_apply
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env accepts named colors" {
  HUED_BACKGROUND="midnightblue" run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

@test "env is case-insensitive" {
  HUED_BACKGROUND="MIDNIGHTBLUE" run _hued_apply
  [[ "$output" == *"${ESC}]11;rgb:19/19/70${BEL}"* ]]
}

# --- 'none' sentinel ---

@test "env bg=none: resets bg even when file sets it" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  HUED_BACKGROUND="none" run _hued_apply
  [[ "$output" == *"$BG_RESET"* ]]
  [[ "$output" == *"${ESC}]10;rgb:ff/ff/ff${BEL}"* ]]
}

@test ".hued bg=none: resets bg, ignoring parent" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  mkdir sub
  printf "background=none\n" > sub/.hued
  cd sub
  run _hued_apply
  [[ "$output" == *"$BG_RESET"* ]]
  # parent's fg is not inherited because the closer .hued breaks the walk
  [[ "$output" == *"$FG_RESET"* ]]
}

@test "env none is case-insensitive" {
  HUED_BACKGROUND="None" run _hued_apply
  [[ "$output" == *"$BG_RESET"* ]]
}

# --- SIGUSR1 trap ---

@test "SIGUSR1 trap is registered after sourcing" {
  run trap -p USR1
  [[ "$output" == *"_hued_apply"* ]]
}
