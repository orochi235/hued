#!/usr/bin/env bats

# hued map serves a page and waits, so these tests run it with --no-open,
# talk to it with curl, and always end it themselves.

HUED="$BATS_TEST_DIRNAME/../bin/hued"

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export XDG_CACHE_HOME="$WORK/.cache"
  mkdir -p "$WORK/taken" "$WORK/new"
  printf 'background=#ff0000\nsfkey=leaf\n' > "$WORK/taken/.hued"
  cd "$WORK/new"
  MAP_PID=""
}

teardown() {
  [[ -n "$MAP_PID" ]] && kill "$MAP_PID" 2>/dev/null || true
  [ -z "${WORK:-}" ] || rm -rf "$WORK"
}

# Start hued map in the background and wait for it to print its URL.
_start() {
  # 3>&-: bats waits on anything still holding its output descriptor.
  HUED_TTY=/dev/null "$HUED" map "$@" --no-open > "$WORK/out" 2>&1 3>&- &
  MAP_PID=$!
  URL=""
  for _ in $(seq 1 100); do
    URL="$(grep -m1 '^http://127.0.0.1:' "$WORK/out" || true)"
    [[ -n "$URL" ]] && return 0
    sleep 0.1
  done
  cat "$WORK/out" >&2
  return 1
}

@test "map: scans the parent directory by default and prints a loopback URL" {
  _start
  grep -q "Scanning $WORK " "$WORK/out"
  grep -q "Found 1 backgrounds in use" "$WORK/out"
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
  grep -q "Wrote $WORK/new/.hued" "$WORK/out"
}

# TERM rather than INT: a shell without job control starts background jobs with INT ignored.
@test "map: a signal ends it without writing" {
  _start
  kill -TERM "$MAP_PID"
  wait "$MAP_PID" || true
  MAP_PID=""
  [ ! -f .hued ]
  grep -q "Nothing written" "$WORK/out"
}

@test "map: takes the directory to scan as an argument" {
  mkdir -p "$WORK/elsewhere/a" "$WORK/elsewhere/b"
  printf 'background=#111111\n' > "$WORK/elsewhere/a/.hued"
  printf 'background=#222222\n' > "$WORK/elsewhere/b/.hued"
  _start "$WORK/elsewhere"
  grep -q "Found 2 backgrounds in use" "$WORK/out"
}

@test "map: a directory that does not exist is an error" {
  run "$HUED" map "$WORK/nope" --no-open
  [ "$status" -eq 1 ]
  [[ "$output" == *"is not a directory"* ]]
}

@test "map: appears in the usage line" {
  run "$HUED" --no-such-flag
  [[ "$output" == *"map [<dir>] [--no-open]"* ]]
}

# Like _start, but for `hued pick`, whose URL goes to stderr and pick to stdout.
_start_pick() {
  HUED_TTY=/dev/null "$HUED" pick "$@" --no-open > "$WORK/out" 2> "$WORK/err" 3>&- &
  MAP_PID=$!
  URL=""
  for _ in $(seq 1 100); do
    URL="$(grep -m1 '^http://127.0.0.1:' "$WORK/err" || true)"
    [[ -n "$URL" ]] && return 0
    sleep 0.1
  done
  cat "$WORK/err" >&2
  return 1
}

@test "map: a pick can set accents and leave the background alone" {
  printf 'background=#123456\n' > .hued
  _start
  run curl -s -X POST -d '{"accent":"#ccff00","accent3":"#ff00ff"}' "${URL/\/\?//use?}"
  wait "$MAP_PID"
  MAP_PID=""
  grep -qx 'background=#123456' .hued
  grep -qx 'accent=#ccff00' .hued
  grep -qx 'accent3=#ff00ff' .hued
}

@test "pick: prints the pick to stdout and writes no file" {
  printf 'background=#123456\n' > .hued
  _start_pick
  ! grep -q Scanning "$WORK/err"
  run curl -s -X POST -d '{"background":"#ffffc4","accent2":"#ff0000"}' "${URL/\/\?//use?}"
  wait "$MAP_PID"
  MAP_PID=""
  [ "$(cat "$WORK/out")" = $'background=#ffffc4\nforeground=#000000\naccent2=#ff0000' ]
  [ "$(cat .hued)" = 'background=#123456' ]
}

@test "pick: scans a directory only when given one" {
  _start_pick "$WORK"
  grep -q "Found 1 backgrounds in use" "$WORK/err"
}

@test "-i: opens the map" {
  HUED_TTY=/dev/null "$HUED" -i --no-open > "$WORK/out" 2>&1 3>&- &
  MAP_PID=$!
  for _ in $(seq 1 100); do
    grep -q '^http://127.0.0.1:' "$WORK/out" && break
    sleep 0.1
  done
  grep -q "Scanning $WORK " "$WORK/out"
}

@test "map: reads the index once seeded; hued set adds to it and pack catches the rest" {
  _start; kill "$MAP_PID"; wait "$MAP_PID" 2>/dev/null || true; MAP_PID=""
  grep -qx "$WORK/taken" "$XDG_CACHE_HOME/hued/index"
  mkdir "$WORK/by-hand" "$WORK/by-set"
  printf 'background=#00ff00\n' > "$WORK/by-hand/.hued"
  (cd "$WORK/by-set" && "$HUED" set bg '#0000ff' >/dev/null)
  _start; kill "$MAP_PID"; wait "$MAP_PID" 2>/dev/null || true; MAP_PID=""
  grep -q "Found 2 backgrounds in use" "$WORK/out"
  "$HUED" pack "$WORK" >/dev/null
  _start
  grep -q "Found 3 backgrounds in use" "$WORK/out"
}
