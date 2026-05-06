_hued_completion() {
  local cur prev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=($(compgen -W "set where" -- "$cur"))
  elif [[ $prev == "set" ]]; then
    local names_file="${HOMEBREW_PREFIX:-/opt/homebrew}/share/hued-names.sh"
    if [[ -f "$names_file" ]]; then
      local colors
      colors=$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')
      COMPREPLY=($(compgen -W "$colors" -- "$cur"))
    fi
  fi
}

complete -F _hued_completion hued
