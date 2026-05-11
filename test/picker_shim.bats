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
