#!/usr/bin/env bats

HUED="$BATS_TEST_DIRNAME/../bin/hued"

setup() {
  TMPDIR="$(mktemp -d)"
  cd "$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR"
}

# --- no-arg: print current colors ---

@test "no args: fails with no .hued file" {
  run "$HUED"
  [ "$status" -eq 1 ]
  [[ "$output" == *"No .hued file found"* ]]
}

@test "no args: prints background and foreground" {
  printf "background=#1a0a0a\nforeground=#ffffff\n" > .hued
  run "$HUED"
  [ "$status" -eq 0 ]
  [[ "$output" == *"background=#1a0a0a"* ]]
  [[ "$output" == *"foreground=#ffffff"* ]]
}

@test "no args: finds .hued in parent directory" {
  printf "background=#1a0a0a\n" > .hued
  mkdir -p sub/dir
  cd sub/dir
  run "$HUED"
  [ "$status" -eq 0 ]
  [[ "$output" == *"background=#1a0a0a"* ]]
}

# --- where ---

@test "where: prints path to .hued file" {
  printf "background=#1a0a0a\n" > .hued
  run "$HUED" where
  [ "$status" -eq 0 ]
  [[ "$output" == *".hued"* ]]
}

@test "where: fails with no .hued file" {
  run "$HUED" where
  [ "$status" -eq 1 ]
}

# --- set ---

@test "set <color>: creates .hued with background" {
  run "$HUED" set "#ff0000"
  [ "$status" -eq 0 ]
  [ -f .hued ]
  grep -q "background=#ff0000" .hued
}

@test "set bg <color>: sets background" {
  run "$HUED" set bg "#ff0000"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
}

@test "set fg <color>: sets foreground" {
  run "$HUED" set fg "#00ff00"
  [ "$status" -eq 0 ]
  grep -q "foreground=#00ff00" .hued
}

@test "set: updates existing background without clobbering foreground" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run "$HUED" set bg "#ff0000"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
  grep -q "foreground=#ffffff" .hued
}

@test "set: creates .hued with repo comment" {
  run "$HUED" set "#ff0000"
  grep -q "github.com/orochi235/hued" .hued
}

# --- pack ---

@test "pack: generates json from directory tree" {
  mkdir -p a b
  printf "background=#111111\n" > a/.hued
  printf "background=#222222\n" > b/.hued
  run "$HUED" pack "$TMPDIR"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"background"'* ]]
  [[ "$output" == *"#111111"* ]]
  [[ "$output" == *"#222222"* ]]
}

@test "pack -o: writes json to file" {
  printf "background=#111111\n" > .hued
  run "$HUED" pack "$TMPDIR" -o out.json
  [ "$status" -eq 0 ]
  [ -f out.json ]
  grep -q "#111111" out.json
}

@test "pack: ignores directories without .hued" {
  mkdir -p a b
  printf "background=#111111\n" > a/.hued
  run "$HUED" pack "$TMPDIR"
  [ "$status" -eq 0 ]
  [[ "$output" != *'"b"'* ]]
}

# --- unpack ---

@test "unpack: creates .hued files from json" {
  mkdir -p target
  printf '{ "%s/target": { "background": "#abcdef" } }' "$TMPDIR" > hued.json
  run "$HUED" unpack hued.json
  [ "$status" -eq 0 ]
  grep -q "background=#abcdef" target/.hued
}

@test "unpack: skips existing .hued without --force" {
  mkdir -p target
  printf "background=#000000\n" > target/.hued
  printf '{ "%s/target": { "background": "#abcdef" } }' "$TMPDIR" > hued.json
  run "$HUED" unpack hued.json
  grep -q "background=#000000" target/.hued
}

@test "unpack --force: overwrites existing .hued" {
  mkdir -p target
  printf "background=#000000\n" > target/.hued
  printf '{ "%s/target": { "background": "#abcdef" } }' "$TMPDIR" > hued.json
  run "$HUED" unpack hued.json --force
  [ "$status" -eq 0 ]
  grep -q "background=#abcdef" target/.hued
}
