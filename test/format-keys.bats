#!/usr/bin/env bats
# The .hued format beyond background/foreground: accent and the branch-*
# minting policy keys. See docs/superpowers/specs/2026-08-22-terminal-identity-design.md

HUED="$BATS_TEST_DIRNAME/../bin/hued"

setup() {
  TMPDIR="$(mktemp -d)"
  cd "$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR"
}

# --- bare output vs -a/--all ---

@test "no args: shows only background and foreground when other keys are present" {
  printf "background=#470013\nforeground=#ffffff\naccent=#ccff00\nbranch-hue=+30deg..+90deg\n" > .hued
  run "$HUED"
  [ "$status" -eq 0 ]
  [[ "$output" == *"background=#470013"* ]]
  [[ "$output" == *"foreground=#ffffff"* ]]
  [[ "$output" != *"accent"* ]]
  [[ "$output" != *"branch-hue"* ]]
}

@test "-a: shows every key in the file" {
  printf "background=#470013\naccent=#ccff00  # limegreen\nbranch-hue=+30deg..+90deg\n" > .hued
  run "$HUED" -a
  [ "$status" -eq 0 ]
  [[ "$output" == *"background=#470013"* ]]
  [[ "$output" == *"accent=#ccff00  # limegreen"* ]]
  [[ "$output" == *"branch-hue=+30deg..+90deg"* ]]
}

@test "--all: same as -a" {
  printf "background=#470013\naccent=#ccff00\n" > .hued
  run "$HUED" --all
  [ "$status" -eq 0 ]
  [[ "$output" == *"accent=#ccff00"* ]]
}

@test "-a: skips comments and blank lines" {
  printf "# https://github.com/orochi235/hued\n\nbackground=#470013\n" > .hued
  run "$HUED" -a
  [ "$status" -eq 0 ]
  [[ "$output" == "background=#470013" ]]
}

@test "-a: fails with no .hued file" {
  run "$HUED" -a
  [ "$status" -eq 1 ]
  [[ "$output" == *"No .hued file found"* ]]
}

# --- set: the unknown-key footgun ---

@test "set accent <color>: writes accent, not background" {
  run "$HUED" set accent "#ccff00"
  [ "$status" -eq 0 ]
  grep -q "^accent=#ccff00" .hued
  ! grep -q "^background=" .hued
}

@test "set <unknown key> <value>: fails loudly and writes nothing" {
  run "$HUED" set bogus "#ccff00"
  [ "$status" -eq 1 ]
  [[ "$output" == *"bogus"* ]]
  [ ! -f .hued ]
}

@test "set <unknown key> <value>: does not touch an existing file" {
  printf "background=#470013\n" > .hued
  run "$HUED" set bogus "#ccff00"
  [ "$status" -eq 1 ]
  grep -q "^background=#470013" .hued
  [ "$(wc -l < .hued)" -eq 1 ]
}

@test "set <color>: a lone argument is still a background color" {
  run "$HUED" set "#ff0000"
  [ "$status" -eq 0 ]
  grep -q "^background=#ff0000" .hued
}

@test "set accent: resolves a named color and keeps the name as a comment" {
  run "$HUED" set accent limegreen
  [ "$status" -eq 0 ]
  grep -q "^accent=#32cd32  # limegreen" .hued
}

@test "set bg: preserves an existing accent line" {
  printf "background=#470013\naccent=#ccff00\n" > .hued
  run "$HUED" set bg "#111111"
  [ "$status" -eq 0 ]
  grep -q "^accent=#ccff00" .hued
  grep -q "^background=#111111" .hued
}

# --- get ---

@test "get accent: returns resolved hex" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#470013\naccent=#ccff00\n" > .hued
  run "$HUED" get accent
  [ "$status" -eq 0 ]
  [ "$output" = "#ccff00" ]
}

@test "get accent: --name names the color" {
  printf "accent=#32cd32\n" > .hued
  run "$HUED" get accent --name
  [ "$status" -eq 0 ]
  [ "$output" = "limegreen" ]
}

@test "get accent: fails when accent is not set" {
  printf "background=#470013\n" > .hued
  run "$HUED" get accent
  [ "$status" -eq 1 ]
}

@test "get branch-hue: prints the stored range verbatim" {
  printf "branch-hue=+30deg..+90deg\n" > .hued
  run "$HUED" get branch-hue
  [ "$status" -eq 0 ]
  [ "$output" = "+30deg..+90deg" ]
}

@test "get branch-hue: --name is rejected on a policy key" {
  printf "branch-hue=+30deg..+90deg\n" > .hued
  run "$HUED" get branch-hue --name
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
}

@test "get: unknown key fails with usage" {
  printf "background=#470013\n" > .hued
  run "$HUED" get bogus
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued get"* ]]
}

# --- branch-* policy values ---

@test "set branch-hue: stores a signed degree range" {
  run "$HUED" set branch-hue "+30deg..+90deg"
  [ "$status" -eq 0 ]
  grep -q "^branch-hue=+30deg\.\.+90deg" .hued
}

@test "set branch-lightness: stores a percent range" {
  run "$HUED" set branch-lightness "22%..38%"
  [ "$status" -eq 0 ]
  grep -q "^branch-lightness=22%\.\.38%" .hued
}

@test "set branch-chroma: stores a percent range" {
  run "$HUED" set branch-chroma "70%..100%"
  [ "$status" -eq 0 ]
  grep -q "^branch-chroma=70%\.\.100%" .hued
}

@test "set branch-hue: accepts a single value as a degenerate range" {
  run "$HUED" set branch-hue "+45deg"
  [ "$status" -eq 0 ]
  grep -q "^branch-hue=+45deg$" .hued
}

@test "set branch-hue: bare numbers gain a deg suffix" {
  run "$HUED" set branch-hue "30..90"
  [ "$status" -eq 0 ]
  grep -q "^branch-hue=30deg\.\.90deg" .hued
}

@test "set branch-lightness: bare numbers gain a percent suffix" {
  run "$HUED" set branch-lightness "22..38"
  [ "$status" -eq 0 ]
  grep -q "^branch-lightness=22%\.\.38%" .hued
}

@test "set branch-hue: rejects a non-numeric value" {
  run "$HUED" set branch-hue "warmish"
  [ "$status" -eq 1 ]
  [[ "$output" == *"warmish"* ]]
  [ ! -f .hued ]
}

@test "set branch-lightness: rejects a color" {
  run "$HUED" set branch-lightness "#ccff00"
  [ "$status" -eq 1 ]
  [ ! -f .hued ]
}

@test "set branch-hue: rejects mixed signed and absolute endpoints" {
  run "$HUED" set branch-hue "+30deg..90deg"
  [ "$status" -eq 1 ]
  [[ "$output" == *"sign"* ]]
  [ ! -f .hued ]
}

@test "set branch-lightness: rejects an ambiguous bare fraction" {
  run "$HUED" set branch-lightness "0.22..0.38"
  [ "$status" -eq 1 ]
  [[ "$output" == *"ambiguous"* ]]
}

@test "set branch-lightness: rejects an empty range endpoint" {
  run "$HUED" set branch-lightness "22%.."
  [ "$status" -eq 1 ]
  [ ! -f .hued ]
}

@test "set branch-hue: rejects a value with no argument" {
  run bash -c "'$HUED' set branch-hue < /dev/null"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage"* ]]
}

# --- unset ---

@test "unset accent: removes accent, keeps background" {
  printf "background=#470013\naccent=#ccff00\n" > .hued
  run "$HUED" unset accent
  [ "$status" -eq 0 ]
  ! grep -q "^accent=" .hued
  grep -q "^background=#470013" .hued
}

@test "unset branch-hue: removes the policy key" {
  printf "background=#470013\nbranch-hue=+30deg..+90deg\n" > .hued
  run "$HUED" unset branch-hue
  [ "$status" -eq 0 ]
  ! grep -q "^branch-hue=" .hued
}

@test "unset accent: errors when accent is not set" {
  printf "background=#470013\n" > .hued
  run "$HUED" unset accent
  [ "$status" -eq 1 ]
  [[ "$output" == *"accent"* ]]
}

@test "unset: rejects an unknown key" {
  printf "background=#470013\n" > .hued
  run "$HUED" unset bogus
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued unset"* ]]
}

# --- sfkey: an SF Symbol name, stored as text ---

@test "set sfkey: stores the name verbatim" {
  run "$HUED" set sfkey paintbrush.pointed.fill
  [ "$status" -eq 0 ]
  grep -qx "sfkey=paintbrush.pointed.fill" .hued
}

@test "set sfkey: a name that is also a color stays a name" {
  run "$HUED" set sfkey leaf
  [ "$status" -eq 0 ]
  grep -qx "sfkey=leaf" .hued
}

@test "set sfkey: rejects whitespace" {
  run "$HUED" set sfkey "leaf fill"
  [ "$status" -eq 1 ]
  [ ! -f .hued ]
}

@test "get sfkey: prints the stored name" {
  printf "background=#470013\nsfkey=leaf\n" > .hued
  run "$HUED" get sfkey
  [ "$status" -eq 0 ]
  [ "$output" = "leaf" ]
}

@test "get sfkey: --name is rejected" {
  printf "sfkey=leaf\n" > .hued
  run "$HUED" get sfkey --name
  [ "$status" -eq 1 ]
}

@test "unset sfkey: removes it, keeps background" {
  printf "background=#470013\nsfkey=leaf\n" > .hued
  run "$HUED" unset sfkey
  [ "$status" -eq 0 ]
  ! grep -q "^sfkey=" .hued
  grep -q "^background=#470013" .hued
}

# --- unpack only treats color keys as colors ---

@test "unpack: non-color values that look like color names are kept" {
  printf '{"%s/r": {"background": "leaf", "sfkey": "leaf", "branch-hue": "30deg..90deg"}}' "$TMPDIR" > export.json
  run "$HUED" unpack export.json
  [ "$status" -eq 0 ]
  grep -qx "sfkey=leaf" r/.hued
  grep -qx "branch-hue=30deg..90deg" r/.hued
  grep -q "^background=#" r/.hued
}
