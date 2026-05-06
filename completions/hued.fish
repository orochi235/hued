set -l names_file "$HOMEBREW_PREFIX/share/hued-names.sh"
set -l subcommands set where pack unpack

complete -c hued -f
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "set"    -d "Create or update .hued in the current directory"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "where"  -d "Print the path to the controlling .hued file"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "pack"   -d "Generate a JSON map of .hued configs from a directory tree"
complete -c hued -n "not __fish_seen_subcommand_from $subcommands" -a "unpack" -d "Restore .hued files from a JSON map"

complete -c hued -n "__fish_seen_subcommand_from set; and not __fish_seen_subcommand_from bg fg" -a "bg" -d "Set background color"
complete -c hued -n "__fish_seen_subcommand_from set; and not __fish_seen_subcommand_from bg fg" -a "fg" -d "Set foreground color"

complete -c hued -n "__fish_seen_subcommand_from pack"   -a "(__fish_complete_directories)"
complete -c hued -n "__fish_seen_subcommand_from pack"   -a "-o" -d "Output file"
complete -c hued -n "__fish_seen_subcommand_from unpack" -a "*.json"
complete -c hued -n "__fish_seen_subcommand_from unpack" -a "--force" -d "Overwrite existing .hued files"

if test -f "$names_file"
  complete -c hued -n "__fish_seen_subcommand_from set" \
    -a "(grep -o '^\[[^]]*\]' $names_file | tr -d '[]')"
end
