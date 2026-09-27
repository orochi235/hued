#!/usr/bin/env bats

# hued map serves a page and waits, so these tests run it with --no-open,
# talk to it with curl, and always end it themselves.

HUED="$BATS_TEST_DIRNAME/../bin/hued"

setup() {
  TMPDIR="$(cd "$(mktemp -d)" && pwd -P)"
  mkdir -p "$TMPDIR/taken" "$TMPDIR/new"
  printf 'background=#ff0000\nsfkey=leaf\n' > "$TMPDIR/taken/.hued"
  cd "$TMPDIR/new"
  MAP_PID=""
}

teardown() {
  [[ -n "$MAP_PID" ]] && kill "$MAP_PID" 2>/dev/null || true
  rm -rf "$TMPDIR"
}

# Start hued map in the background and wait for it to print its URL.
_start() {
  # 3>&-: bats waits on anything still holding its output descriptor.
  HUED_TTY=/dev/null "$HUED" map "$@" --no-open > "$TMPDIR/out" 2>&1 3>&- &
  MAP_PID=$!
  URL=""
  for _ in $(seq 1 100); do
    URL="$(grep -m1 '^http://127.0.0.1:' "$TMPDIR/out" || true)"
    [[ -n "$URL" ]] && return 0
    sleep 0.1
  done
  cat "$TMPDIR/out" >&2
  return 1
}

@test "map: scans the parent directory by default and prints a loopback URL" {
  _start
  grep -q "Scanning $TMPDIR " "$TMPDIR/out"
  grep -q "Found 1 backgrounds in use" "$TMPDIR/out"
  [[ "$URL" == http://127.0.0.1:*"/?t="* ]]
}

@test "map: serves the page with the token and refuses without it" {
  _start
  run curl -s -o /dev/null -w '%{http_code}' "$URL"
  [ "$output" = "200" ]
  run curl -s -o /dev/null -w '%{http_code}' "${URL%%\?*}"
  [ "$output" = "403" ]
}

@test "map: a pick writes .hued and ends the command" {
  _start
  run curl -s -X POST -d '{"background":"#320053","sfkey":"bolt"}' "${URL/\/\?//use?}"
  [[ "$output" == *'"written"'* ]]
  wait "$MAP_PID"
  MAP_PID=""
  grep -qx 'background=#320053' .hued
  grep -qx 'sfkey=bolt' .hued
  ! grep -q '^foreground=' .hued
  grep -q "Wrote $TMPDIR/new/.hued" "$TMPDIR/out"
}

# TERM rather than INT: a shell without job control starts background jobs with INT ignored.
@test "map: a signal ends it without writing" {
  _start
  kill -TERM "$MAP_PID"
  wait "$MAP_PID" || true
  MAP_PID=""
  [ ! -f .hued ]
  grep -q "Nothing written" "$TMPDIR/out"
}

@test "map: takes the directory to scan as an argument" {
  mkdir -p "$TMPDIR/elsewhere/a" "$TMPDIR/elsewhere/b"
  printf 'background=#111111\n' > "$TMPDIR/elsewhere/a/.hued"
  printf 'background=#222222\n' > "$TMPDIR/elsewhere/b/.hued"
  _start "$TMPDIR/elsewhere"
  grep -q "Found 2 backgrounds in use" "$TMPDIR/out"
}

@test "map: a directory that does not exist is an error" {
  run "$HUED" map "$TMPDIR/nope" --no-open
  [ "$status" -eq 1 ]
  [[ "$output" == *"is not a directory"* ]]
}

@test "map: appears in the usage line" {
  run "$HUED" --no-such-flag
  [[ "$output" == *"map [<dir>] [--no-open]"* ]]
}
