#!/usr/bin/env bats

HUED="$BATS_TEST_DIRNAME/../bin/hued"

setup() {
  WORK="$(mktemp -d)"
  export XDG_CACHE_HOME="$WORK/.cache"
  cd "$WORK"
}

teardown() {
  [ -z "${WORK:-}" ] || rm -rf "$WORK"
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

@test "-v: prints version" {
  run "$HUED" -v
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^hued\ [0-9]+\.[0-9]+\.[0-9]+$ ]]
}

@test "--version: prints version" {
  run "$HUED" --version
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^hued\ [0-9]+\.[0-9]+\.[0-9]+$ ]]
}

@test "version: prints version" {
  run "$HUED" version
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^hued\ [0-9]+\.[0-9]+\.[0-9]+$ ]]
}

@test "fork: copies inherited bg+fg from ancestor into new ./.hued" {
  printf "background=#112233\nforeground=#aabbcc\n" > .hued
  mkdir sub
  cd sub
  run "$HUED" fork
  [ "$status" -eq 0 ]
  grep -q "^background=#112233" .hued
  grep -q "^foreground=#aabbcc" .hued
}

@test "fork: copies only the channels the ancestor defines" {
  printf "background=#112233\n" > .hued
  mkdir sub
  cd sub
  run "$HUED" fork
  [ "$status" -eq 0 ]
  grep -q "^background=#112233" .hued
  ! grep -q "^foreground=" .hued
}

@test "fork: errors if ./.hued already exists" {
  printf "background=#112233\n" > .hued
  mkdir sub
  printf "background=#445566\n" > sub/.hued
  cd sub
  run "$HUED" fork
  [ "$status" -eq 1 ]
  [[ "$output" == *"already exists"* ]]
  grep -q "^background=#445566" .hued
}

@test "fork: errors when no ancestor .hued exists" {
  run "$HUED" fork
  [ "$status" -eq 1 ]
  [[ "$output" == *"no ancestor"* ]]
}

@test "fork: walks past intermediate dirs without .hued" {
  printf "background=#112233\n" > .hued
  mkdir -p a/b/c
  cd a/b/c
  run "$HUED" fork
  [ "$status" -eq 0 ]
  grep -q "^background=#112233" .hued
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

# --- color names ---

@test "names: xkcd-only name resolves" {
  "$HUED" set emerald
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#01a049" ]]
}

@test "names: multi-word name resolves with spaces stripped" {
  "$HUED" set "baby poop green"
  a=$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')
  rm -f .hued
  "$HUED" set babypoopgreen
  b=$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')
  [[ "$a" == "$b" ]]
  [[ "$a" == "#8f9805" ]]
}

@test "names: canonical CSS keywords keep their CSS values" {
  for pair in red:#ff0000 green:#008000 blue:#0000ff gray:#808080 \
              navy:#000080 teal:#008080 lime:#00ff00 yellow:#ffff00; do
    name="${pair%%:*}"; want="${pair##*:}"
    rm -f .hued
    "$HUED" set "$name"
    got=$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')
    [[ "$got" == "$want" ]] || { echo "$name resolved to $got, want $want"; return 1; }
  done
}

@test "names: the two carried-over X11 names take their xkcd values" {
  "$HUED" set navyblue
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#001146" ]]
  rm -f .hued
  "$HUED" set violetred
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#a50055" ]]
}

@test "names: dropped X11 numbered variant no longer resolves" {
  run "$HUED" set gray50
  [ "$status" -eq 0 ]
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "gray50" ]]
}

@test "names: a name with regex metacharacters passes through literally" {
  for name in '.*' 'g.ay' '*' '[a-z]'; do
    rm -f .hued
    "$HUED" set "$name"
    got=$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')
    [[ "$got" == "$name" ]] || { echo "set '$name' wrote '$got'"; return 1; }
  done
}

@test "names: a hyphenated name resolves like its unspaced spelling" {
  "$HUED" set baby-blue
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#a2cffe" ]]
}

# --- -x / HUED_LOOKUP_PREFER_XKCD ---

@test "-x: prefers the xkcd value for a shared name" {
  "$HUED" -x set red
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#e50000" ]]
}

@test "-x: leaves xkcd-only names unchanged" {
  "$HUED" -x set emerald
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#01a049" ]]
}

@test "no -x: uses the CSS value" {
  "$HUED" set red
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#ff0000" ]]
}

@test "-x: works before any subcommand" {
  printf "background=#888888\n" > .hued
  run "$HUED" -x where
  [ "$status" -eq 0 ]
  [[ "$output" == *"/.hued" ]]
}

@test "HUED_LOOKUP_PREFER_XKCD: set to 1 prefers the xkcd value" {
  HUED_LOOKUP_PREFER_XKCD=1 "$HUED" set red
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#e50000" ]]
}

@test "HUED_LOOKUP_PREFER_XKCD: off values are treated as off" {
  for off in "" 0 false no off n FALSE No OFF N; do
    rm -f .hued
    HUED_LOOKUP_PREFER_XKCD="$off" "$HUED" set red
    got=$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')
    [[ "$got" == "#ff0000" ]] || { echo "HUED_LOOKUP_PREFER_XKCD=$off gave $got, want #ff0000"; return 1; }
  done
}

@test "HUED_LOOKUP_PREFER_XKCD: arbitrary truthy values are treated as on" {
  for on in 1 true yes on TRUE; do
    rm -f .hued
    HUED_LOOKUP_PREFER_XKCD="$on" "$HUED" set red
    got=$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')
    [[ "$got" == "#e50000" ]] || { echo "HUED_LOOKUP_PREFER_XKCD=$on gave $got, want #e50000"; return 1; }
  done
}

@test "HUED_LOOKUP_PREFER_XKCD: -x still works when the variable is unset" {
  unset HUED_LOOKUP_PREFER_XKCD
  "$HUED" -x set red
  [[ "$(grep ^background= .hued | cut -d= -f2 | awk '{print $1}')" == "#e50000" ]]
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
  printf "background=rgb(26,10,10)\n" > .hued
  run "$HUED" get bg
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires 'pastel'"* ]]
}

@test "get --name: names an exact hex" {
  printf "background=#01a049\n" > .hued
  run "$HUED" get bg --name
  [ "$status" -eq 0 ]
  [[ "$output" == "emerald" ]]
}

@test "get --name: names the nearest color for an inexact hex" {
  printf "background=#01a04a\n" > .hued
  run "$HUED" get bg --name
  [ "$status" -eq 0 ]
  [[ "$output" == "emerald" ]]
}

@test "get --name: -x prefers an xkcd reading" {
  printf "background=#e50000\n" > .hued
  run "$HUED" -x get bg --name
  [ "$status" -eq 0 ]
  [[ "$output" == "red" ]]
}

@test "get --name: fails when the channel is unset" {
  printf "foreground=#ffffff\n" > .hued
  run "$HUED" get bg --name
  [ "$status" -eq 1 ]
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

@test "mod bg darken: bare number is percent" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg darken 20
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.2 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg darken: bare fraction is rejected as ambiguous" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken 0.2
  [ "$status" -eq 1 ]
  [[ "$output" == *"ambiguous"* ]]
  [[ "$output" == *"20%"* ]]
}

@test "mod bg lightness: ambiguity message keeps the sign" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  run "$HUED" mod bg lightness +0.5
  [ "$status" -eq 1 ]
  [[ "$output" == *"ambiguous"* ]]
  [[ "$output" == *"+50%"* ]]
}

@test "mod bg darken: explicit fractional percent is allowed" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg darken 0.2%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.002 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg darken: non-numeric amount fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken banana
  [ "$status" -eq 1 ]
  [[ "$output" == *"not a number"* ]]
}

@test "mod: missing channel fails with usage" {
  run "$HUED" mod
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage: hued mod"* ]]
}

@test "mod: invalid channel is treated as an unknown op" {
  run "$HUED" mod xyz darken 20%
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown op"* ]]
  [[ "$output" == *"expected bg|fg"* ]]
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
  run "$HUED" mod bg darken 20%
  [ "$status" -eq 1 ]
  [[ "$output" == *"background not set"* ]]
}

@test "mod bg: unknown op fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg frobnicate 20%
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown op"* ]]
}

@test "mod bg darken: missing amount fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires an amount"* ]]
}

@test "mod bg darken: 20% darkens the background" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken 20%
  [ "$status" -eq 0 ]
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.2 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod fg lighten: works on foreground" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "foreground=#222222\n" > .hued
  "$HUED" mod fg lighten 10%
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
  "$HUED" mod bg desaturate 50%
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

@test "mod bg rotate: accepts a negative angle" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg rotate -90
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel rotate -- -90 '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg rotate: accepts a negative angle with deg suffix" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg rotate -90deg
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel rotate -- -90 '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg rotate: non-numeric angle fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  run "$HUED" mod bg rotate sideways
  [ "$status" -eq 1 ]
  [[ "$output" == *"degrees"* ]]
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
  "$HUED" mod bg mix '#0000ff' 25%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel mix --fraction 0.25 '#0000ff' '#ff0000' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod: channel defaults to background" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod darken 20%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.2 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod: unknown leading token fails as unknown op" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod xyz 20%
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown op"* ]]
}

@test "mod bg darken: negative amount lightens" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg darken -10%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel lighten 0.1 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg saturate: negative amount desaturates" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#cc4444\n" > .hued
  "$HUED" mod bg saturate -25%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel desaturate 0.25 '#cc4444' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg: chained ops apply in order" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg darken 10% rotate 30deg
  new=$(grep ^background= .hued | cut -d= -f2)
  step1=$(pastel darken 0.1 '#888888' | pastel format hex)
  expected=$(pastel rotate -- 30 "$step1" | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg: a chain writes the key exactly once" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg darken 10% rotate 30deg desaturate 5%
  [ "$(grep -c '^background=' .hued)" -eq 1 ]
}

@test "mod bg: a failing op in a chain leaves the file untouched" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  run "$HUED" mod bg darken 10% rotate sideways
  [ "$status" -eq 1 ]
  [[ "$(grep ^background= .hued | cut -d= -f2)" == "#888888" ]]
}

@test "mod bg mix: ratio in a chain is distinguished from a following op" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg mix '#0000ff' darken 10%
  new=$(grep ^background= .hued | cut -d= -f2)
  step1=$(pastel mix --fraction 0.5 '#0000ff' '#ff0000' | pastel format hex)
  expected=$(pastel darken 0.1 "$step1" | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg mix: negative ratio fails" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  run "$HUED" mod bg mix '#0000ff' -25%
  [ "$status" -eq 1 ]
  [[ "$output" == *"cannot be negative"* ]]
}

@test "mod bg lightness: signed value is relative" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg lightness +10%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel lighten 0.1 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg lightness: negative signed value darkens" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg lightness -10%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.1 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg lightness: unsigned value sets HSL lightness absolutely" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg lightness 70%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel set hsl-lightness 0.7 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

# #336699 already sits at HSL L=40%, so this pins the scale to HSL: a Lab
# lightness assignment would move it.
@test "mod bg lightness: setting the value it already has is a no-op" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg lightness 40%
  new=$(grep ^background= .hued | cut -d= -f2)
  [[ "$new" == "#336699" ]]
}

@test "mod bg saturation: unsigned value sets HSL saturation absolutely" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg saturation 90%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel set hsl-saturation 0.9 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg saturation: signed value is relative" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#cc4444\n" > .hued
  "$HUED" mod bg saturation -25%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel desaturate 0.25 '#cc4444' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg hue: unsigned value sets hue absolutely" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg hue 200deg
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel set hsl-hue 200 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg hue: signed value rotates" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg hue +30deg
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel rotate -- 30 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg lighten: negative amount darkens" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#888888\n" > .hued
  "$HUED" mod bg lighten -10%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel darken 0.1 '#888888' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg desaturate: negative amount saturates" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#cc4444\n" > .hued
  "$HUED" mod bg desaturate -25%
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel saturate 0.25 '#cc4444' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg mix: an explicit ratio can be followed by another op" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg mix '#0000ff' 25% darken 10%
  new=$(grep ^background= .hued | cut -d= -f2)
  step1=$(pastel mix --fraction 0.25 '#0000ff' '#ff0000' | pastel format hex)
  expected=$(pastel darken 0.1 "$step1" | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg mix: works as a non-leading op in a chain" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg darken 10% mix '#0000ff' 25%
  new=$(grep ^background= .hued | cut -d= -f2)
  step1=$(pastel darken 0.1 '#ff0000' | pastel format hex)
  expected=$(pastel mix --fraction 0.25 '#0000ff' "$step1" | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg: complement in the middle of a chain" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg complement darken 10%
  new=$(grep ^background= .hued | cut -d= -f2)
  step1=$(pastel complement '#ff0000' | pastel format hex)
  expected=$(pastel darken 0.1 "$step1" | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg: to-gray in the middle of a chain" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ff0000\n" > .hued
  "$HUED" mod bg to-gray lighten 10%
  new=$(grep ^background= .hued | cut -d= -f2)
  step1=$(pastel to-gray '#ff0000' | pastel format hex)
  expected=$(pastel lighten 0.1 "$step1" | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg hue: negative signed value rotates backwards" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg hue -30deg
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel rotate -- -30 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg saturation: a bare number is read as percent" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#336699\n" > .hued
  "$HUED" mod bg saturation 90
  new=$(grep ^background= .hued | cut -d= -f2)
  expected=$(pastel set hsl-saturation 0.9 '#336699' | pastel format hex)
  [[ "$new" == "$expected" ]]
}

@test "mod bg: fails when pastel not installed" {
  command -v pastel >/dev/null 2>&1 && skip "pastel is installed"
  printf "background=#ff0000\n" > .hued
  run "$HUED" mod bg darken 20%
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
  run "$HUED" pack "$WORK"
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
  run "$HUED" pack "$WORK" -o out.json
  [ "$status" -eq 0 ]
  [ -f out.json ]
  grep -q "#111111" out.json
}

@test "pack: ignores directories without .hued" {
  mkdir -p a b
  printf "background=#111111\n" > a/.hued
  run "$HUED" pack "$WORK"
  [ "$status" -eq 0 ]
  [[ "$output" != *'"b"'* ]]
}

# --- unpack ---

@test "unpack: creates .hued files from json" {
  mkdir -p target
  printf '{ "%s/target": { "background": "#abcdef" } }' "$WORK" > hued.json
  run "$HUED" unpack hued.json
  [ "$status" -eq 0 ]
  grep -q "background=#abcdef" target/.hued
}

@test "unpack: skips existing .hued without --force" {
  mkdir -p target
  printf "background=#000000\n" > target/.hued
  printf '{ "%s/target": { "background": "#abcdef" } }' "$WORK" > hued.json
  run "$HUED" unpack hued.json
  grep -q "background=#000000" target/.hued
}

@test "unpack --force: overwrites existing .hued" {
  mkdir -p target
  printf "background=#000000\n" > target/.hued
  printf '{ "%s/target": { "background": "#abcdef" } }' "$WORK" > hued.json
  run "$HUED" unpack hued.json --force
  [ "$status" -eq 0 ]
  grep -q "background=#abcdef" target/.hued
}

# --- names file resolution under install layouts ---

@test "set: resolves named color under share/ layout (brew install)" {
  mkdir -p prefix/bin prefix/share
  cp "$HUED" prefix/bin/hued
  cp "$BATS_TEST_DIRNAME/../hued-names.sh" prefix/share/hued-names.sh
  run "$PWD/prefix/bin/hued" set bg goldenrod
  [ "$status" -eq 0 ]
  grep -q "^background=#daa520  # goldenrod$" .hued
}

# --- inline name comments ---

@test "set bg: keeps named color as inline comment" {
  run "$HUED" set bg "aliceblue"
  [ "$status" -eq 0 ]
  grep -q "^background=#f0f8ff  # aliceblue$" .hued
}

@test "set bg: hex input gets no inline comment" {
  run "$HUED" set bg "#ff0000"
  [ "$status" -eq 0 ]
  grep -q "^background=#ff0000$" .hued
}

@test "set bg: none gets no inline comment" {
  run "$HUED" set bg "none"
  [ "$status" -eq 0 ]
  grep -q "^background=none$" .hued
}

@test "get: ignores inline name comment" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#f0f8ff  # aliceblue\n" > .hued
  run "$HUED" get bg
  [ "$status" -eq 0 ]
  [[ "$output" == *"f0f8ff"* ]]
}

@test "mod: ignores inline name comment when reading current" {
  command -v pastel >/dev/null 2>&1 || skip "pastel not installed"
  printf "background=#ffffff  # white\n" > .hued
  run "$HUED" mod bg to-gray
  [ "$status" -eq 0 ]
  grep -q "^background=#[0-9a-f]\{6\}$" .hued
}

@test "pack: strips inline name comment to bare hex" {
  printf "background=#f0f8ff  # aliceblue\n" > .hued
  run "$HUED" pack "$WORK"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"#f0f8ff"'* ]]
  [[ "$output" != *"aliceblue"* ]]
}

@test "unpack: normalizes named color to hex with comment" {
  mkdir -p target
  printf '{ "%s/target": { "background": "aliceblue" } }' "$WORK" > hued.json
  run "$HUED" unpack hued.json
  [ "$status" -eq 0 ]
  grep -q "^background=#f0f8ff  # aliceblue$" target/.hued
}

@test "unpack: normalizes a hyphenated, mixed-case name" {
  mkdir -p target
  printf '{ "%s/target": { "background": "Baby-Blue" } }' "$WORK" > hued.json
  run "$HUED" unpack hued.json
  [ "$status" -eq 0 ]
  grep -q "^background=#a2cffe  # Baby-Blue$" target/.hued
}

@test "unpack: leaves hex values untouched" {
  mkdir -p target
  printf '{ "%s/target": { "background": "#abcdef" } }' "$WORK" > hued.json
  run "$HUED" unpack hued.json
  [ "$status" -eq 0 ]
  grep -q "^background=#abcdef$" target/.hued
}

@test "fork: inherits resolved hex from commented ancestor" {
  printf "background=#f0f8ff  # aliceblue\n" > .hued
  mkdir sub
  cd sub
  run "$HUED" fork
  [ "$status" -eq 0 ]
  grep -q "^background=#f0f8ff$" .hued
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
  _ends_with_newline "$HUED" pack "$WORK"
}

@test "unpack: output ends with newline" {
  mkdir -p target
  printf '{ "%s/target": { "background": "#abcdef" } }' "$WORK" > hued.json
  _ends_with_newline "$HUED" unpack hued.json
}
