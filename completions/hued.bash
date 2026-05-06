_hued_completion() {
  local cur prev pprev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  pprev="${COMP_WORDS[COMP_CWORD-2]:-}"

  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=($(compgen -W "set where" -- "$cur"))
  elif [[ $prev == "set" ]]; then
    COMPREPLY=($(compgen -W "bg fg" -- "$cur"))
    # also complete colors directly for backward compat
    local names_file="${HOMEBREW_PREFIX:-/opt/homebrew}/share/hued-names.sh"
    if [[ -f "$names_file" ]]; then
      local colors
      colors=$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')
      COMPREPLY+=($(compgen -W "$colors" -- "$cur"))
    fi
  elif [[ "$pprev" == "set" && ( "$prev" == "bg" || "$prev" == "fg" ) ]]; then
    local names_file="${HOMEBREW_PREFIX:-/opt/homebrew}/share/hued-names.sh"
    if [[ -f "$names_file" ]]; then
      local colors
      colors=$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')
      COMPREPLY=($(compgen -W "$colors" -- "$cur"))
    fi
  fi
}

complete -F _hued_completion hued
