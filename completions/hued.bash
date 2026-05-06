_hued_completion() {
  local cur prev pprev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  pprev="${COMP_WORDS[COMP_CWORD-2]:-}"

  local names_file="${HOMEBREW_PREFIX:-/opt/homebrew}/share/hued-names.sh"

  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=($(compgen -W "set where pack unpack" -- "$cur"))
  elif [[ $prev == "set" ]]; then
    COMPREPLY=($(compgen -W "bg fg" -- "$cur"))
    [[ -f "$names_file" ]] && COMPREPLY+=($(compgen -W "$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')" -- "$cur"))
  elif [[ "$pprev" == "set" && ( "$prev" == "bg" || "$prev" == "fg" ) ]]; then
    [[ -f "$names_file" ]] && COMPREPLY=($(compgen -W "$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')" -- "$cur"))
  elif [[ $prev == "pack" ]]; then
    COMPREPLY=($(compgen -d -- "$cur"))
  elif [[ $prev == "-o" ]]; then
    COMPREPLY=($(compgen -f -- "$cur"))
  elif [[ $prev == "unpack" ]]; then
    COMPREPLY=($(compgen -f -X '!*.json' -- "$cur"))
  elif [[ "$pprev" == "unpack" ]]; then
    COMPREPLY=($(compgen -W "--force" -- "$cur"))
  fi
}

complete -F _hued_completion hued
