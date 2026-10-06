_hued_completion() {
  local cur prev pprev names_file mod_ops keys color_keys
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  pprev="${COMP_WORDS[COMP_CWORD-2]:-}"
  names_file="${HOMEBREW_PREFIX:-/opt/homebrew}/share/hued-names.sh"
  mod_ops="darken lighten saturate desaturate rotate complement to-gray mix lightness saturation hue"
  keys="bg fg accent accent2 accent3 branch-hue branch-lightness branch-chroma sfkey slug"
  color_keys="bg fg accent accent2 accent3"
  COMPREPLY=()

  if [[ $COMP_CWORD -eq 1 ]]; then
    mapfile -t COMPREPLY < <(compgen -W "set unset fork get mod apply where resolve pack unpack map pick -a" -- "$cur")
  elif [[ $prev == "get" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "$keys" -- "$cur")
  elif [[ $prev == "unset" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "$keys" -- "$cur")
  elif [[ $prev == "mod" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "bg fg $mod_ops" -- "$cur")
  elif [[ "$pprev" == "mod" && ( "$prev" == "bg" || "$prev" == "fg" ) ]]; then
    mapfile -t COMPREPLY < <(compgen -W "$mod_ops" -- "$cur")
  elif [[ $prev == "resolve" ]]; then
    if [[ -f "$names_file" ]]; then
      mapfile -t COMPREPLY < <(
        compgen -W "$(grep -o '^ *\[[^]]*\]' "$names_file" | tr -d '[] ' | grep -v '^xkcd:')" -- "$cur"
      )
    fi
  elif [[ $prev == "set" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "$keys" -- "$cur")
    if [[ -f "$names_file" ]]; then
      mapfile -t -O "${#COMPREPLY[@]}" COMPREPLY < <(
        compgen -W "$(grep -o '^ *\[[^]]*\]' "$names_file" | tr -d '[] ' | grep -v '^xkcd:')" -- "$cur"
      )
    fi
  elif [[ "$pprev" == "set" && " $color_keys " == *" $prev "* ]]; then
    if [[ -f "$names_file" ]]; then
      mapfile -t COMPREPLY < <(
        compgen -W "$(grep -o '^ *\[[^]]*\]' "$names_file" | tr -d '[] ' | grep -v '^xkcd:')" -- "$cur"
      )
    fi
  elif [[ $prev == "pack" ]]; then
    mapfile -t COMPREPLY < <(compgen -d -- "$cur")
  elif [[ $prev == "map" ]]; then
    mapfile -t COMPREPLY < <(compgen -d -- "$cur")
    mapfile -t -O "${#COMPREPLY[@]}" COMPREPLY < <(compgen -W "--no-open" -- "$cur")
  elif [[ "$pprev" == "map" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "--no-open" -- "$cur")
  elif [[ $prev == "-o" ]]; then
    mapfile -t COMPREPLY < <(compgen -f -- "$cur")
  elif [[ $prev == "unpack" ]]; then
    mapfile -t COMPREPLY < <(compgen -f -- "$cur")
  elif [[ "$pprev" == "unpack" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "--force" -- "$cur")
  fi
}

complete -F _hued_completion hued
