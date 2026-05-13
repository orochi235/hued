#!/usr/bin/env bats

# Tests for bash completion logic.
# Sources the completion script and invokes _hued_completion directly
# by simulating COMP_WORDS and COMP_CWORD.

COMPLETION="$BATS_TEST_DIRNAME/../completions/hued.bash"

setup() {
  source "$COMPLETION"
  COMPREPLY=()
}

_complete() {
  COMP_WORDS=("$@")
  COMP_CWORD=$(( ${#COMP_WORDS[@]} - 1 ))
  _hued_completion
}

# --- subcommands ---

@test "completes top-level subcommands" {
  _complete hued ""
  [[ "${COMPREPLY[*]}" == *"set"* ]]
  [[ "${COMPREPLY[*]}" == *"get"* ]]
  [[ "${COMPREPLY[*]}" == *"mod"* ]]
  [[ "${COMPREPLY[*]}" == *"where"* ]]
  [[ "${COMPREPLY[*]}" == *"resolve"* ]]
  [[ "${COMPREPLY[*]}" == *"pack"* ]]
  [[ "${COMPREPLY[*]}" == *"unpack"* ]]
}

@test "get: suggests bg and fg" {
  _complete hued get ""
  [[ "${COMPREPLY[*]}" == *"bg"* ]]
  [[ "${COMPREPLY[*]}" == *"fg"* ]]
}

@test "mod: suggests bg and fg" {
  _complete hued mod ""
  [[ "${COMPREPLY[*]}" == *"bg"* ]]
  [[ "${COMPREPLY[*]}" == *"fg"* ]]
}

@test "mod bg: suggests transform ops" {
  _complete hued mod bg ""
  [[ "${COMPREPLY[*]}" == *"darken"* ]]
  [[ "${COMPREPLY[*]}" == *"lighten"* ]]
  [[ "${COMPREPLY[*]}" == *"mix"* ]]
}

@test "filters subcommands by prefix" {
  _complete hued "p"
  [[ "${COMPREPLY[*]}" == *"pack"* ]]
  [[ "${COMPREPLY[*]}" != *"set"* ]]
  [[ "${COMPREPLY[*]}" != *"where"* ]]
}

# --- set ---

@test "set: suggests bg and fg" {
  _complete hued set ""
  [[ "${COMPREPLY[*]}" == *"bg"* ]]
  [[ "${COMPREPLY[*]}" == *"fg"* ]]
}

@test "set bg: does not suggest --force" {
  _complete hued set bg ""
  [[ "${COMPREPLY[*]}" != *"--force"* ]]
}

@test "set fg: does not suggest --force" {
  _complete hued set fg ""
  [[ "${COMPREPLY[*]}" != *"--force"* ]]
}

# --- pack ---

@test "pack: does not suggest --force" {
  _complete hued pack ""
  [[ "${COMPREPLY[*]}" != *"--force"* ]]
}

@test "pack: does not suggest bg or fg" {
  _complete hued pack ""
  [[ "${COMPREPLY[*]}" != *"bg"* ]]
  [[ "${COMPREPLY[*]}" != *"fg"* ]]
}

# --- unpack ---

@test "unpack: suggests --force" {
  _complete hued unpack "somefile.json" ""
  [[ "${COMPREPLY[*]}" == *"--force"* ]]
}

@test "unpack: does not suggest --force as first arg" {
  _complete hued unpack ""
  [[ "${COMPREPLY[*]}" != *"--force"* ]]
}

@test "unpack: does not suggest bg or fg" {
  _complete hued unpack "somefile.json" ""
  [[ "${COMPREPLY[*]}" != *"bg"* ]]
  [[ "${COMPREPLY[*]}" != *"fg"* ]]
}
