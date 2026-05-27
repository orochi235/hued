_hued_completion() {
  local cur prev pprev names_file
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  pprev="${COMP_WORDS[COMP_CWORD-2]:-}"
  names_file="${HOMEBREW_PREFIX:-/opt/homebrew}/share/hued-names.sh"
  COMPREPLY=()

  if [[ $COMP_CWORD -eq 1 ]]; then
    mapfile -t COMPREPLY < <(compgen -W "set unset fork get mod where resolve pack unpack" -- "$cur")
  elif [[ $prev == "get" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "bg fg" -- "$cur")
  elif [[ $prev == "unset" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "bg fg" -- "$cur")
  elif [[ $prev == "mod" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "bg fg" -- "$cur")
  elif [[ "$pprev" == "mod" && ( "$prev" == "bg" || "$prev" == "fg" ) ]]; then
    mapfile -t COMPREPLY < <(compgen -W "darken lighten saturate desaturate rotate complement to-gray mix" -- "$cur")
  elif [[ $prev == "resolve" ]]; then
    if [[ -f "$names_file" ]]; then
      mapfile -t COMPREPLY < <(
        compgen -W "$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')" -- "$cur"
      )
    fi
  elif [[ $prev == "set" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "bg fg" -- "$cur")
    if [[ -f "$names_file" ]]; then
      mapfile -t -O "${#COMPREPLY[@]}" COMPREPLY < <(
        compgen -W "$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')" -- "$cur"
      )
    fi
  elif [[ "$pprev" == "set" && ( "$prev" == "bg" || "$prev" == "fg" ) ]]; then
    if [[ -f "$names_file" ]]; then
      mapfile -t COMPREPLY < <(
        compgen -W "$(grep -o '^\[[^]]*\]' "$names_file" | tr -d '[]')" -- "$cur"
      )
    fi
  elif [[ $prev == "pack" ]]; then
    mapfile -t COMPREPLY < <(compgen -d -- "$cur")
  elif [[ $prev == "-o" ]]; then
    mapfile -t COMPREPLY < <(compgen -f -- "$cur")
  elif [[ $prev == "unpack" ]]; then
    mapfile -t COMPREPLY < <(compgen -f -- "$cur")
  elif [[ "$pprev" == "unpack" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "--force" -- "$cur")
  fi
}

complete -F _hued_completion hued
