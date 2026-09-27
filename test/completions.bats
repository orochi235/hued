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
  [[ "${COMPREPLY[*]}" == *"apply"* ]]
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

@test "mod: suggests transform ops without a channel" {
  _complete hued mod ""
  [[ "${COMPREPLY[*]}" == *"darken"* ]]
  [[ "${COMPREPLY[*]}" == *"lightness"* ]]
  [[ "${COMPREPLY[*]}" == *"to-gray"* ]]
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

# --- color names ---

# The names file ships every key indented two spaces, so a '^\[' pattern
# silently matches nothing.
@test "set: completes color names from the names file" {
  prefix="$(mktemp -d)"
  mkdir -p "$prefix/share"
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" "$prefix/share/hued-names.sh"
  HOMEBREW_PREFIX="$prefix" _complete hued set "re"
  rm -rf "$prefix"
  [[ "${COMPREPLY[*]}" == *"red"* ]]
}

@test "set bg: completes color names but not xkcd: keys" {
  prefix="$(mktemp -d)"
  mkdir -p "$prefix/share"
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" "$prefix/share/hued-names.sh"
  HOMEBREW_PREFIX="$prefix" _complete hued set bg ""
  rm -rf "$prefix"
  [[ "${COMPREPLY[*]}" == *"aliceblue"* ]]
  [[ "${COMPREPLY[*]}" != *"xkcd:"* ]]
}

@test "completions: all three shells read the indented key rows" {
  for f in completions/hued.bash completions/hued.fish completions/_hued; do
    grep -qF '^ *\[' "$BATS_TEST_DIRNAME/../$f" || {
      echo "$f does not allow for indented key rows"; return 1; }
    grep -qF "grep -v '^xkcd:'" "$BATS_TEST_DIRNAME/../$f" || {
      echo "$f does not filter xkcd: keys"; return 1; }
  done
}

# --- mod ops ---

@test "completions: all three shells list the new HSL ops" {
  for f in completions/hued.bash completions/hued.fish completions/_hued; do
    grep -qE '(^| )lightness( |$|")' "$BATS_TEST_DIRNAME/../$f" || {
      echo "missing lightness in $f"; return 1; }
    grep -qE '(^| )saturation( |$|")' "$BATS_TEST_DIRNAME/../$f" || {
      echo "missing saturation in $f"; return 1; }
    grep -qE '(^| )hue( |$|")' "$BATS_TEST_DIRNAME/../$f" || {
      echo "missing hue in $f"; return 1; }
  done
}

# --- format keys beyond bg/fg ---

@test "get: suggests accent and the branch policy keys" {
  _complete hued get ""
  [[ "${COMPREPLY[*]}" == *"accent"* ]]
  [[ "${COMPREPLY[*]}" == *"branch-hue"* ]]
  [[ "${COMPREPLY[*]}" == *"branch-lightness"* ]]
  [[ "${COMPREPLY[*]}" == *"branch-chroma"* ]]
}

@test "unset: suggests accent and the branch policy keys" {
  _complete hued unset ""
  [[ "${COMPREPLY[*]}" == *"accent"* ]]
  [[ "${COMPREPLY[*]}" == *"branch-hue"* ]]
}

@test "set: suggests accent and the branch policy keys" {
  _complete hued set ""
  [[ "${COMPREPLY[*]}" == *"accent"* ]]
  [[ "${COMPREPLY[*]}" == *"branch-chroma"* ]]
}

@test "set accent: completes color names" {
  prefix="$(mktemp -d)"
  mkdir -p "$prefix/share"
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" "$prefix/share/hued-names.sh"
  HOMEBREW_PREFIX="$prefix" _complete hued set accent "re"
  rm -rf "$prefix"
  [[ "${COMPREPLY[*]}" == *"red"* ]]
}

@test "set branch-hue: does not complete color names" {
  prefix="$(mktemp -d)"
  mkdir -p "$prefix/share"
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" "$prefix/share/hued-names.sh"
  HOMEBREW_PREFIX="$prefix" _complete hued set branch-hue "re"
  rm -rf "$prefix"
  [[ "${COMPREPLY[*]}" != *"red"* ]]
}

@test "completions: all three shells offer the new keys" {
  for f in completions/hued.bash completions/hued.fish completions/_hued; do
    for key in accent branch-hue branch-lightness branch-chroma sfkey; do
      grep -qF "$key" "$BATS_TEST_DIRNAME/../$f" || {
        echo "missing $key in $f"; return 1; }
    done
  done
}

@test "set sfkey: does not complete color names" {
  prefix="$(mktemp -d)"
  mkdir -p "$prefix/share"
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" "$prefix/share/hued-names.sh"
  HOMEBREW_PREFIX="$prefix" _complete hued set sfkey "le"
  rm -rf "$prefix"
  [[ "${COMPREPLY[*]}" != *"lemon"* ]]
}

# --- map ---

@test "completes map as a subcommand" {
  _complete hued "ma"
  [[ " ${COMPREPLY[*]} " == *" map "* ]]
}

@test "map: suggests --no-open" {
  _complete hued map "--"
  [[ "${COMPREPLY[*]}" == *"--no-open"* ]]
  _complete hued map "somedir" ""
  [[ "${COMPREPLY[*]}" == *"--no-open"* ]]
}

@test "map: every completion script knows the command" {
  cd "$BATS_TEST_DIRNAME/.."
  for f in completions/hued.bash completions/hued.fish completions/_hued; do
    grep -q -- '--no-open' "$f"
    grep -qw 'map' "$f"
  done
}
