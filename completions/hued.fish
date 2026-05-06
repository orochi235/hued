set -l names_file "$HOMEBREW_PREFIX/share/hued-names.sh"

complete -c hued -f
complete -c hued -n "not __fish_seen_subcommand_from set where" -a "set"   -d "Create or update .hued in the current directory"
complete -c hued -n "not __fish_seen_subcommand_from set where" -a "where" -d "Print the path to the controlling .hued file"
complete -c hued -n "__fish_seen_subcommand_from set; and not __fish_seen_subcommand_from bg fg" -a "bg" -d "Set background color"
complete -c hued -n "__fish_seen_subcommand_from set; and not __fish_seen_subcommand_from bg fg" -a "fg" -d "Set foreground color"

if test -f "$names_file"
  complete -c hued -n "__fish_seen_subcommand_from set" \
    -a "(grep -o '^\[[^]]*\]' $names_file | tr -d '[]')"
end
