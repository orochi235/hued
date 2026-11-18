# TODO

- **`hued unpack --dry-run` and target-root remapping.** `src/huedmap/files.py:unpack` now
  checks the whole manifest before writing and never clobbers a file it didn't mean to, but
  it can't show what it would do first, and a manifest packed on another machine writes to
  that machine's absolute paths. Wants a `--dry-run` that prints each path's outcome
  (write, skip, overwrite) and a way to map the manifest's root onto a local one. (filed
  2026-11-15 from automated review)
- **Smoke-test the installed layout, not the checkout.** The bats and pytest suites run from
  the source tree, so they can't catch the Homebrew formula (`Formula/hued.rb` in `orochi235/homebrew-tap`,
  which lists every installed file by hand) missing a new script or package. A clean-prefix
  smoke would lay out `bin/`, `share/`, and `libexec/hued/` the way the formula does, then
  source the bash, zsh, and fish hooks, run `hued-py huedmap` imports, and resolve a named
  color with the checkout off `PATH`. The release workflow could run it against the tagged
  archive. (filed 2026-11-15 from automated review)
