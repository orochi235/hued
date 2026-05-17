# hued macOS theme-change watcher (opt-in)

## Problem

iTerm2 (and some other macOS terminals) reset per-window OSC 10/11 colors back
to the profile preset when macOS switches between light and dark appearance.
Since `hued` only re-emits OSC 10/11 on the next shell prompt, hued-set windows
look unhued until the user hits Enter.

## Fix

A tiny daemon subscribes to `AppleInterfaceThemeChangedNotification` and runs
`hued reapply` on each switch, which signals all interactive shells of the user
to re-run `_hued_apply`.

## Install (manual)

```sh
# Build the watcher
clang -framework Foundation -o hued-watch-macos hued-watch-macos.m

# Install the binary and plist
sudo cp hued-watch-macos /usr/local/bin/
mkdir -p ~/Library/LaunchAgents
sed -e "s|@@HUED_WATCH_BIN@@|/usr/local/bin/hued-watch-macos|" \
    -e "s|@@HUED_BIN@@|$(command -v hued)|" \
    com.github.orochi235.hued.watch.plist \
    > ~/Library/LaunchAgents/com.github.orochi235.hued.watch.plist

# Load
launchctl load ~/Library/LaunchAgents/com.github.orochi235.hued.watch.plist
```

## Install (Homebrew)

The Homebrew formula installs the binary and a templated plist but does **not**
start the service. To opt in:

```sh
brew services start hued
```

To disable:

```sh
brew services stop hued
```

## Verify

Toggle System Settings → Appearance between Light and Dark. Any open shell in a
directory with an active `.hued` should immediately restore its colors. Logs:
`/tmp/hued-watch.out`, `/tmp/hued-watch.err`.

## Porting to other OSes

The contract is simple: when the OS appearance changes, run `hued reapply`.
That subcommand sends `SIGUSR1` to the user's `zsh`/`bash`/`fish` processes,
each of which has a trap installed by hued's shell hook to re-apply colors.

- **GNOME:** `gsettings monitor org.gnome.desktop.interface color-scheme | while read -r _; do hued reapply; done`
- **KDE:** subscribe to D-Bus signal `org.kde.kdeglobals` or watch
  `~/.config/kdeglobals` for changes.
- **Windows:** listen for `WM_SETTINGCHANGE` with `lParam` "ImmersiveColorSet".

Drop your adapter under `contrib/<os>/` and PRs welcome.
