#!/usr/bin/env bats

# ---------------------------------------------------------------------------
# Tests for bin/hued-pick shim and bin/hued -i wiring.
#
# These tests do NOT start the picker interactively (that requires a TTY).
# They verify the shim's path-resolution logic, Python invocability, and
# the CLI flag wiring, all without a real terminal.
# ---------------------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HUED_PICK="$REPO_ROOT/bin/hued-pick"
HUED="$REPO_ROOT/bin/hued"

@test "bin/hued-pick exists and is executable" {
  [[ -x "$HUED_PICK" ]]
}

@test "bin/hued-pick shebang is bash" {
  head -1 "$HUED_PICK" | grep -q 'env bash'
}

@test "bin/hued-pick --help exits 0 and mentions picker" {
  run "$HUED_PICK" --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ [Pp]icker ]]
}

@test "bin/hued-pick resolves src/picker in source tree" {
  # Confirm PYTHONPATH resolution prints no 'cannot find picker' error
  run "$HUED_PICK" --help 2>&1
  [[ ! "$output" =~ "cannot find picker package" ]]
}

@test "bin/hued -i flag is recognized (no TTY exits nonzero, not 'unknown command')" {
  # Without a TTY the picker will fail (can't enter raw mode), but it must NOT
  # print the 'Usage:' line from the catch-all — that would mean -i is unrecognized.
  run "$HUED" -i </dev/null 2>&1 || true
  [[ ! "$output" =~ "Usage: hued" ]]
}

@test "bin/hued shows updated usage including -i" {
  run "$HUED" --no-such-flag 2>&1 || true
  [[ "$output" =~ \-i ]]
}

@test "bin/hued -i: missing foreground in .hued does not abort before invoking picker" {
  # Regression: grep -m1 '^foreground=' returns 1 when the key is absent;
  # under `set -euo pipefail`, this once killed the script before the picker ran.
  tmpdir=$(mktemp -d)
  printf "background=#112233\n" > "$tmpdir/.hued"
  mkdir -p "$tmpdir/stubbin"
  cat > "$tmpdir/stubbin/hued-pick" <<'STUB'
#!/usr/bin/env bash
echo "PICKER_CALLED args=$*" >&2
exit 1
STUB
  chmod +x "$tmpdir/stubbin/hued-pick"
  # Run hued from the stub dir so $(dirname "$0")/hued-pick resolves to the stub
  cp "$HUED" "$tmpdir/stubbin/hued"
  run bash -c "cd '$tmpdir' && '$tmpdir/stubbin/hued' -i </dev/null 2>&1"
  rm -rf "$tmpdir"
  [[ "$output" =~ PICKER_CALLED ]]
  [[ "$output" =~ --bg\ \#112233 ]]
  [[ ! "$output" =~ --fg ]]
}

@test "bin/hued -i: missing background in .hued does not abort before invoking picker" {
  tmpdir=$(mktemp -d)
  printf "foreground=#aabbcc\n" > "$tmpdir/.hued"
  mkdir -p "$tmpdir/stubbin"
  cat > "$tmpdir/stubbin/hued-pick" <<'STUB'
#!/usr/bin/env bash
echo "PICKER_CALLED args=$*" >&2
exit 1
STUB
  chmod +x "$tmpdir/stubbin/hued-pick"
  cp "$HUED" "$tmpdir/stubbin/hued"
  run bash -c "cd '$tmpdir' && '$tmpdir/stubbin/hued' -i </dev/null 2>&1"
  rm -rf "$tmpdir"
  [[ "$output" =~ PICKER_CALLED ]]
  [[ "$output" =~ --fg\ \#aabbcc ]]
  [[ ! "$output" =~ --bg ]]
}

@test "bin/hued -i: no .hued at all does not abort before invoking picker" {
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/stubbin"
  cat > "$tmpdir/stubbin/hued-pick" <<'STUB'
#!/usr/bin/env bash
echo "PICKER_CALLED args=$*" >&2
exit 1
STUB
  chmod +x "$tmpdir/stubbin/hued-pick"
  cp "$HUED" "$tmpdir/stubbin/hued"
  # cd to a deep tmp path so _hued_find walks up without finding a .hued
  run bash -c "cd '$tmpdir' && HOME='$tmpdir' '$tmpdir/stubbin/hued' -i </dev/null 2>&1"
  rm -rf "$tmpdir"
  [[ "$output" =~ PICKER_CALLED ]]
}

@test "bin/hued-pick fails gracefully when python3 is absent" {
  # Temporarily shadow python3 with a no-op that exits 127.
  # We verify the shim itself doesn't crash before exec.
  run bash -c '
    mkdir -p /tmp/hued_test_bin
    printf "#!/bin/sh\nexit 127\n" > /tmp/hued_test_bin/python3
    chmod +x /tmp/hued_test_bin/python3
    PATH=/tmp/hued_test_bin:$PATH '"$HUED_PICK"' --help
    exitcode=$?
    rm -rf /tmp/hued_test_bin
    exit $exitcode
  '
  # Exit code should be 127 (python3 not found), not 1 (shim logic error)
  [ "$status" -eq 127 ]
}
