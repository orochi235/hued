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

@test "unset bg: removes background, keeps foreground" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run "$HUED" unset bg
  [ "$status" -eq 0 ]
  ! grep -q "^background=" .hued
  grep -q "^foreground=#ffffff" .hued
}

@test "unset fg: removes foreground, keeps background" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run "$HUED" unset fg
  [ "$status" -eq 0 ]
  grep -q "^background=#000000" .hued
  ! grep -q "^foreground=" .hued
}

@test "unset: accepts long names (background/foreground)" {
  printf "background=#000000\nforeground=#ffffff\n" > .hued
  run "$HUED" unset foreground
  [ "$status" -eq 0 ]
  ! grep -q "^foreground=" .hued
}

@test "unset: errors when no .hued exists" {
  run "$HUED" unset bg
  [ "$status" -eq 1 ]
  [[ "$output" == *"no .hued"* ]]
}

@test "unset: errors when channel not set" {
  printf "background=#000000\n" > .hued
  run "$HUED" unset fg
  [ "$status" -eq 1 ]
  [[ "$output" == *"foreground not set"* ]]
}

@test "unset: rejects bad channel" {
  printf "background=#000000\n" > .hued
  run "$HUED" unset bogus
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued unset"* ]]
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

@test "set bg: accepts hex without leading #" {
  run "$HUED" set bg "ff0000"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
}

@test "set bg: accepts 3-char hex and expands to 6-char" {
  run "$HUED" set bg "#f00"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
}

@test "set bg: accepts 3-char hex without leading #" {
  run "$HUED" set bg "f00"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
}

@test "set bg: normalizes hex to lowercase" {
  run "$HUED" set bg "FF0000"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
}

@test "set bg: resolves named color to hex" {
  run "$HUED" set bg "aliceblue"
  [ "$status" -eq 0 ]
  grep -q "background=#f0f8ff" .hued
}

@test "set bg: accepts background as keyword" {
  run "$HUED" set background "#ff0000"
  [ "$status" -eq 0 ]
  grep -q "background=#ff0000" .hued
}

@test "set fg: accepts foreground as keyword" {
  run "$HUED" set foreground "#00ff00"
  [ "$status" -eq 0 ]
  grep -q "foreground=#00ff00" .hued
}

# --- get ---

@test "get: missing channel fails with usage" {
  printf "background=#1a0a0a\n" > .hued
  run "$HUED" get
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued get"* ]]
}

@test "get: invalid channel fails with usage" {
  printf "background=#1a0a0a\n" > .hued
  run "$HUED" get xyz
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued get"* ]]
}

@test "get bg: fails with no .hued file" {
  run "$HUED" get bg
  [ "$status" -eq 1 ]
  [[ "$output" == *"No .hued file found"* ]]
}

@test "get bg: fails (empty output) when channel not set" {
  printf "foreground=#ffffff\n" > .hued
  run "$HUED" get bg
  [ "$status" -eq 1 ]
  [[ -z "$output" ]]
}

@test "get bg: returns resolved hex" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#1a0a0a\n" > .hued
  run "$HUED" get bg
  [ "$status" -eq 0 ]
  [[ "$output" == "#1a0a0a" ]]
}

@test "get fg: returns resolved hex" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "foreground=#ffffff\n" > .hued
  run "$HUED" get fg
  [ "$status" -eq 0 ]
  [[ "$output" == "#ffffff" ]]
}

@test "get background: same as bg" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#1a0a0a\n" > .hued
  run "$HUED" get background
  [ "$status" -eq 0 ]
  [[ "$output" == "#1a0a0a" ]]
}

@test "get foreground: same as fg" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "foreground=#ffffff\n" > .hued
  run "$HUED" get foreground
  [ "$status" -eq 0 ]
  [[ "$output" == "#ffffff" ]]
}

@test "get bg: re-resolves unnormalized value in .hued" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=red\n" > .hued
  run "$HUED" get bg
  [ "$status" -eq 0 ]
  [[ "$output" == "#ff0000" ]]
}

@test "get bg: fails when value is unresolvable" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=notacolor\n" > .hued
  run "$HUED" get bg
  [ "$status" -ne 0 ]
}

@test "get bg: fails when pastel is not installed" {
  command -v pastel >/dev/null 2>&1 && skip "pastel is installed"
  printf "background=#1a0a0a\n" > .hued
  run "$HUED" get bg
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires 'pastel'"* ]]
}

# --- set: stdin piping ---

@test "set bg: reads color from stdin when no arg" {
  echo '#ff0000' | "$HUED" set bg
  grep -q "background=#ff0000" .hued
}

@test "set fg: reads color from stdin when no arg" {
  echo '#00ff00' | "$HUED" set fg
  grep -q "foreground=#00ff00" .hued
}

@test "set: reads stdin and writes to bg when no channel and no arg" {
  echo '#0000ff' | "$HUED" set
  grep -q "background=#0000ff" .hued
}

@test "set bg: stdin value is normalized" {
  echo '#FFF' | "$HUED" set bg
  grep -q "background=#ffffff" .hued
}

@test "set bg: explicit arg wins over stdin" {
  echo '#000000' | "$HUED" set bg "#ff0000"
  grep -q "background=#ff0000" .hued
  ! grep -q "background=#000000" .hued
}

@test "set bg: trailing whitespace stripped from piped color" {
  printf '#abcdef \n' | "$HUED" set bg
  grep -q "background=#abcdef" .hued
}

@test "set bg: empty stdin still errors" {
  run bash -c "printf '' | '$HUED' set bg"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued set bg"* ]]
}

# --- mod ---

@test "mod: missing channel fails with usage" {
  run "$HUED" mod
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued mod"* ]]
}

@test "mod: invalid channel fails" {
  run "$HUED" mod xyz darken 0.2
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued mod"* ]]
}

@test "mod bg: missing op fails with usage" {
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued mod"* ]]
}

@test "mod bg: fails when channel not set" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "foreground=#ffffff\n" > .hued
  run "$HUED" mod bg darken 0.2
  [ "$status" -eq 1 ]
  [[ "$output" == *"background not set"* ]]
}

@test "mod bg: unknown op fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg frobnicate 0.2
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown op"* ]]
}

@test "mod bg darken: missing amount fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage:"* ]]
}

@test "mod bg darken: 0.2 darkens the background" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken 0.2
  [ "$status" -eq 0 ]
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.2 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg darken: accepts percent" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg darken 20%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.2 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod fg lighten: works on foreground" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "foreground=#222222\n" > .hued
  "$HUED" mod fg lighten 0.1
  new=$(grep ^foreground= .hued | cut -d= -f2)
  expected=$(pastel lighten 0.1 '#222222' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg saturate: applies saturate" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#806060\n" > .hued
  "$HUED" mod bg saturate 50%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel saturate 0.5 '#806060' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg desaturate: applies desaturate" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg desaturate 0.5
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel desaturate 0.5 '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg rotate: accepts plain degrees" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg rotate 90
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel rotate 90 '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg rotate: accepts 'deg' suffix" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg rotate 90deg
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel rotate 90 '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg complement: no extra arg required" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg complement
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel complement '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg to-gray: applies to-gray" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg to-gray
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel to-gray '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg mix: default ratio 0.5" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg mix '#0000ff'
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel mix --fraction 0.5 '#0000ff' '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg mix: accepts explicit ratio" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg mix '#0000ff' 0.25
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel mix --fraction 0.25 '#0000ff' '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg mix: ratio percent" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg mix '#0000ff' 25%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel mix --fraction 0.25 '#0000ff' '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg: fails when pastel not installed" {
  command -v pastel >/dev/null 2>&1 && skip "pastel is installed"
  printf "background=#ff0000\n" > .hued
  run "$HUED" mod bg darken 0.2
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires 'pastel'"* ]]
}

# --- resolve ---

@test "resolve: missing arg fails with usage" {
  run "$HUED" resolve
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued resolve"* ]]
}

@test "resolve: fails with clear error when pastel is not installed" {
  command -v pastel >/dev/null 2>&1 && skip "pastel is installed"
  run "$HUED" resolve "#abc"
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires 'pastel'"* ]]
}

@test "resolve: returns canonical #rrggbb for 6-char hex" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  run "$HUED" resolve "#FF0000"
  [ "$status" -eq 0 ]
  [[ "$output" == "#ff0000" ]]
}

@test "resolve: accepts hex without leading #" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  run "$HUED" resolve "ff0000"
  [ "$status" -eq 0 ]
  [[ "$output" == "#ff0000" ]]
}

@test "resolve: expands 3-char hex" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  run "$HUED" resolve "#f00"
  [ "$status" -eq 0 ]
  [[ "$output" == "#ff0000" ]]
}

@test "resolve: resolves CSS named color" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  run "$HUED" resolve "aliceblue"
  [ "$status" -eq 0 ]
  [[ "$output" == "#f0f8ff" ]]
}

@test "resolve: fails on unrecognized color" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  run "$HUED" resolve "notacolor"
  [ "$status" -ne 0 ]
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

@test "pack: defaults to current directory when no dir given" {
  mkdir -p a
  printf "background=#abcdef\n" > a/.hued
  run "$HUED" pack
  [ "$status" -eq 0 ]
  [[ "$output" == *"#abcdef"* ]]
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

# --- trailing newlines ---

_ends_with_newline() {
  local cmd=("$@")
  "${cmd[@]}" > _out.txt
  [[ "$(tail -c1 _out.txt | od -An -tx1 | tr -d ' \n')" == "0a" ]]
}

@test "no args: output ends with newline" {
  printf "background=#1a0a0a\n" > .hued
  _ends_with_newline "$HUED"
}

@test "where: output ends with newline" {
  printf "background=#1a0a0a\n" > .hued
  _ends_with_newline "$HUED" where
}

@test "set: output ends with newline" {
  _ends_with_newline "$HUED" set "#ff0000"
}

@test "resolve: output ends with newline" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  _ends_with_newline "$HUED" resolve "#abc"
}

@test "pack: output ends with newline" {
  printf "background=#111111\n" > .hued
  _ends_with_newline "$HUED" pack "$TMPDIR"
}

@test "unpack: output ends with newline" {
  mkdir -p target
  printf '{ "%s/target": { "background": "#abcdef" } }' "$TMPDIR" > hued.json
  _ends_with_newline "$HUED" unpack hued.json
}
