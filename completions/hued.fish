set -l names_file "$HOMEBREW_PREFIX/share/hued-names.sh"
set -l subcommands set unset fork get mod where resolve pack unpack
set -l mod_ops darken lighten saturate desaturate rotate complement to-gray mix

complete -c hued -f
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "set"     -d "Create or update .hued in the current directory"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "unset"   -d "Remove a channel from .hued in the current directory"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "fork"    -d "Materialize inherited colors into a new .hued in the current directory"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "get"     -d "Print the resolved hex for a channel"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "mod"     -d "Apply a pastel transform to a channel and save the result"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "where"   -d "Print the path to the controlling .hued file"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "resolve" -d "Print canonical #rrggbb hex for a color (via pastel)"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "pack"    -d "Generate a JSON map of .hued configs from a directory tree"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "unpack"  -d "Restore .hued files from a JSON map"

complete -c hued -n "__fish_seen_subcommand_from set; and not __fish_seen_subcommand_from bg fg" -a "bg" -d "Set background color"
complete -c hued -n "__fish_seen_subcommand_from set; and not __fish_seen_subcommand_from bg fg" -a "fg" -d "Set foreground color"
complete -c hued -n "__fish_seen_subcommand_from get; and not __fish_seen_subcommand_from bg fg" -a "bg" -d "Background channel"
complete -c hued -n "__fish_seen_subcommand_from get; and not __fish_seen_subcommand_from bg fg" -a "fg" -d "Foreground channel"
complete -c hued -n "__fish_seen_subcommand_from unset; and not __fish_seen_subcommand_from bg fg" -a "bg" -d "Background channel"
complete -c hued -n "__fish_seen_subcommand_from unset; and not __fish_seen_subcommand_from bg fg" -a "fg" -d "Foreground channel"
complete -c hued -n "__fish_seen_subcommand_from mod; and not __fish_seen_subcommand_from bg fg" -a "bg" -d "Background channel"
complete -c hued -n "__fish_seen_subcommand_from mod; and not __fish_seen_subcommand_from bg fg" -a "fg" -d "Foreground channel"
complete -c hued -n "__fish_seen_subcommand_from mod; and __fish_seen_subcommand_from bg fg; and not __fish_seen_subcommand_from $mod_ops" -a "$mod_ops"

complete -c hued -n "__fish_seen_subcommand_from pack"   -a "(__fish_complete_directories)"
complete -c hued -n "__fish_seen_subcommand_from pack"   -a "-o" -d "Output file"
complete -c hued -n "__fish_seen_subcommand_from unpack" -a "*.json"
complete -c hued -n "__fish_seen_subcommand_from unpack" -a "--force" -d "Overwrite existing .hued files"

if test -f "$names_file"
  complete -c hued -n "__fish_seen_subcommand_from set" \
    -a "(grep -o '^\[[^]]*\]' $names_file | tr -d '[]')"
  complete -c hued -n "__fish_seen_subcommand_from resolve" \
    -a "(grep -o '^\[[^]]*\]' $names_file | tr -d '[]')"
end
